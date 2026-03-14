"""
auth.py — Synchronous OAuth2 PKCE login for Medicover.
Ported from MediCony/src/medicover/auth.py (async → sync).
"""

import base64
import hashlib
import random
import re
import string
import time
import uuid
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


class LoginError(Exception):
    pass


class TokenExchangeError(Exception):
    pass


def _generate_code_challenge(code_verifier: str) -> str:
    sha256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(sha256).decode("utf-8").rstrip("=")


def _slack_get(session: requests.Session, headers: dict, url: str, **kwargs) -> requests.Response:
    """GET with a small random delay to simulate human browsing."""
    time.sleep(random.uniform(0.5, 2.0))
    return session.get(url, headers=headers, **kwargs)


def _retrieve_app_version(session: requests.Session, headers: dict) -> str:
    url = "https://online24.medicover.pl/env-config.js"
    response = _slack_get(session, headers, url)
    if response.status_code != 200:
        raise requests.RequestException(f"Failed to retrieve app version, status: {response.status_code}")
    match = re.search(r'VITE_VERSION:\s*"([^"]+)"', response.text)
    if not match:
        raise ValueError("VITE_VERSION not found in env-config.js")
    return match.group(1)


def _skip_mfa_gate(session: requests.Session, headers: dict, mfa_path: str) -> str | None:
    """
    Skip the MFA-gate page if it appears.
    Returns the next redirect path, or None if no MFA gate was present.
    """
    login_url = "https://login-online24.medicover.pl"
    response = _slack_get(session, headers, f"{login_url}{mfa_path}", allow_redirects=False)

    if 'formaction="/Account/MfaGate?handler=SkipMfaGate"' not in response.text:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    csrf_input = soup.find("input", {"name": "__RequestVerificationToken"})
    return_url_input = soup.find("input", {"name": "Input.ReturnUrl"})
    skip_button = soup.find(attrs={"formaction": "/Account/MfaGate?handler=SkipMfaGate"})

    if not csrf_input or not return_url_input:
        raise ValueError("Failed to extract MFA form fields")

    csrf_token = csrf_input.get("value")
    return_url = return_url_input.get("value")
    skip_action = str(skip_button.get("formaction")) if skip_button else "/Account/MfaGate?handler=SkipMfaGate"

    skip_data = {
        "Input.ReturnUrl": return_url,
        "__RequestVerificationToken": csrf_token,
    }
    skip_headers = {
        **headers,
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": login_url,
        "Referer": f"{login_url}{mfa_path}",
    }
    resp = session.post(
        urljoin(login_url, skip_action),
        data=skip_data,
        headers=skip_headers,
        allow_redirects=False,
    )
    if resp.status_code != 302:
        raise requests.RequestException(f"Failed to skip MFA gate, status: {resp.status_code}")
    return resp.headers.get("Location")


def login(card_number: str, password: str) -> tuple[requests.Session, dict]:
    """
    Perform synchronous OAuth2 PKCE login against Medicover.
    Returns (session, headers) where headers["Authorization"] = "Bearer <token>".
    """
    session = requests.Session()
    headers = {
        "User-Agent": UserAgent(platforms="desktop").random,
        "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # PKCE params
    state = "".join(random.choices(string.ascii_lowercase + string.digits, k=32))
    device_id = str(uuid.uuid4())
    code_verifier = "".join(uuid.uuid4().hex for _ in range(3))
    code_challenge = _generate_code_challenge(code_verifier)

    app_version = _retrieve_app_version(session, headers)

    login_url = "https://login-online24.medicover.pl"
    oidc_redirect = "https://online24.medicover.pl/signin-oidc"
    auth_params = (
        f"?client_id=web&redirect_uri={oidc_redirect}&response_type=code"
        f"&scope=openid+offline_access+profile&state={state}&code_challenge={code_challenge}"
        f"&code_challenge_method=S256&response_mode=query&ui_locales=pl&app_version={app_version}"
        f"&previous_app_version={app_version}&device_id={device_id}&device_name=Chrome"
    )

    # Step 1: Initialize authorization
    resp = _slack_get(
        session, headers,
        f"{login_url}/connect/authorize{auth_params}",
        allow_redirects=False,
    )
    if resp.status_code != 302 or not resp.headers.get("Location"):
        raise LoginError(f"Authorization init failed, status: {resp.status_code}")

    # Step 2: Load login form (append timestamp)
    next_url = f"{resp.headers['Location']}%26ts%3D{int(time.time_ns() / 1_000_000)}"
    resp = _slack_get(session, headers, next_url, allow_redirects=False)

    soup = BeautifulSoup(resp.content, "html.parser")
    csrf_input = soup.find("input", {"name": "__RequestVerificationToken"})
    if not csrf_input:
        raise LoginError("CSRF token not found in login form")
    csrf_token = csrf_input.get("value")

    return_url_input = soup.find("input", {"name": "Input.ReturnUrl"})
    return_url = return_url_input.get("value") if return_url_input else f"/connect/authorize/callback{auth_params}"

    form = soup.find("form")
    form_action = urljoin(login_url, form.get("action")) if form and form.get("action") else next_url

    # Step 3: Submit credentials
    login_data = {
        "Input.ReturnUrl": return_url,
        "Input.LoginType": "FullLogin",
        "Input.Username": card_number,
        "Input.Password": password,
        "Input.Button": "login",
        "Input.IsSimpleAccessRegulationAccepted": "true",
        "__RequestVerificationToken": csrf_token,
    }
    post_headers = {
        **headers,
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://login-online24.medicover.pl",
        "Referer": next_url,
    }
    resp = session.post(form_action, data=login_data, headers=post_headers, allow_redirects=False)
    if "INVALID_CREDENTIALS" in resp.text or resp.status_code != 302:
        raise LoginError(f"Login failed (HTTP {resp.status_code})")

    next_url = resp.headers.get("Location")
    if not next_url:
        raise LoginError("No Location header after credential POST")

    # Step 4: Skip MFA gate if present
    if "MfaGate" in next_url:
        next_url = _skip_mfa_gate(session, headers, next_url)
        if not next_url:
            raise LoginError("MFA gate present but could not be skipped")

    # Step 5: Follow redirect to get authorization code
    resp = _slack_get(session, headers, f"{login_url}{next_url}", allow_redirects=False)
    redirect_location = resp.headers.get("Location", "")
    query = urlparse(redirect_location).query
    code_dict = parse_qs(query, keep_blank_values=True)
    code_list = code_dict.get("code")
    if not code_list:
        raise LoginError(f"No 'code' in redirect URL: {redirect_location}")
    code = code_list[0]

    # Step 6: Exchange code for tokens
    token_data = {
        "grant_type": "authorization_code",
        "redirect_uri": oidc_redirect,
        "code": code,
        "code_verifier": code_verifier,
        "client_id": "web",
    }
    resp = session.post(f"{login_url}/connect/token", data=token_data, headers=headers)
    if resp.status_code != 200:
        raise TokenExchangeError(f"Token exchange failed, status: {resp.status_code}: {resp.text}")

    bearer_token = resp.json()["access_token"]
    headers["Authorization"] = f"Bearer {bearer_token}"
    return session, headers
