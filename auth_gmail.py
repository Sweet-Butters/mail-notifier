"""Step 1 검증: Gmail API 인증 후 받은편지함 최근 5개 메일의 제목/발신자 출력.

첫 실행 시 콘솔에 인증 URL이 출력된다. 사용자가 Windows 브라우저에 붙여넣어
동의 후, localhost 콜백이 자동으로 토큰을 받는다 (token.json에 저장).
이후 실행은 브라우저 없이 동작한다.
"""

from __future__ import annotations

import os.path
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"


def get_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            print("=" * 70, flush=True)
            print("아래 URL을 복사해서 Windows 브라우저에 붙여넣으세요:", flush=True)
            print("=" * 70, flush=True)
            sys.stdout.flush()
            creds = flow.run_local_server(
                port=0,
                open_browser=False,
                authorization_prompt_message="\n{url}\n",
                success_message="인증 완료! 이 탭은 닫아도 됩니다.",
            )
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def main() -> None:
    service = get_service()
    resp = (
        service.users()
        .messages()
        .list(userId="me", maxResults=5, q="in:inbox")
        .execute()
    )
    msgs = resp.get("messages", [])
    if not msgs:
        print("받은편지함이 비어있습니다.")
        return
    print(f"받은편지함 최근 {len(msgs)}개:")
    for m in msgs:
        full = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=m["id"],
                format="metadata",
                metadataHeaders=["Subject", "From"],
            )
            .execute()
        )
        headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}
        print(f"  • {headers.get('Subject', '(제목 없음)')}")
        print(f"    From: {headers.get('From', '')}")


if __name__ == "__main__":
    main()
