#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebPageMon 폐쇄망용 로컬 서버 + 프록시
=====================================================================
외부 인터넷이 안 되는 사내 폐쇄망에서, 다른 내부 호스트의 페이지를
브라우저(WebPageMon)가 읽을 수 있게 해주는 작은 서버입니다.

- 파이썬 "표준 라이브러리"만 사용합니다 (pip 설치 불필요).
- 같은 폴더의 index.html 등 정적 파일을 서빙합니다.
- /proxy?url=<대상주소>  로 요청하면, 서버가 대상 페이지를 대신
  가져와 CORS 헤더를 붙여 돌려줍니다. (브라우저 교차출처 문제 해결)

실행 (index.html 과 같은 폴더에서):
    python3 server.py              # http://0.0.0.0:8000
    python3 server.py 8080         # 포트 변경
    python3 server.py 8080 127.0.0.1   # 바인드 호스트 지정

그다음 브라우저에서  http://<서버주소>:8000  접속  (★ file:// 로 열지 마세요)
앱에서  비교 프록시 →  '내부 프록시 서버 (/proxy)'  선택.
"""

import sys, os, ssl, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs
from http.server import SimpleHTTPRequestHandler, HTTPServer
try:
    from http.server import ThreadingHTTPServer            # Python 3.7+
except ImportError:                                        # Python 3.6
    from socketserver import ThreadingMixIn
    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

# 사내 HTTPS 자체서명 인증서 대응: 인증서 검증을 끕니다. 필요 없으면 False.
INSECURE_SSL = True

# 실제 브라우저처럼 보이게 하는 요청 헤더 (UA 기반 차단 회피용)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


class Handler(SimpleHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") == "/proxy":
            return self.handle_proxy(parse_qs(parsed.query))
        return SimpleHTTPRequestHandler.do_GET(self)   # 정적 파일 서빙

    def handle_proxy(self, qs):
        target = (qs.get("url") or [""])[0]
        if not target:
            return self._text(400, "Missing ?url= parameter")
        try:
            ctx = ssl._create_unverified_context() if INSECURE_SSL else None
            req = urllib.request.Request(target, headers=BROWSER_HEADERS)
            resp = urllib.request.urlopen(req, timeout=20, context=ctx)
            body = resp.read()
            ctype = resp.headers.get("Content-Type", "text/html")
            status = resp.getcode()
        except urllib.error.HTTPError as e:        # 대상이 4xx/5xx 반환
            try: body = e.read()
            except Exception: body = b""
            ctype = e.headers.get("Content-Type", "text/plain") if e.headers else "text/plain"
            status = e.code
        except Exception as e:                     # 연결 실패 등
            return self._text(502, "Upstream error: %s" % e)
        self.send_response(status)
        self.send_header("Content-Type", ctype)    # 원본 인코딩(EUC-KR 등) 유지
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, code, msg):
        data = msg.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass   # 콘솔 로그 소음 제거 (요청 로그를 보고 싶으면 이 줄을 지우세요)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
    os.chdir(os.path.dirname(os.path.abspath(__file__)))   # index.html 위치 기준 서빙
    print("WebPageMon 서버 실행: http://%s:%d   (정적 파일 + /proxy?url=...)" % (host, port))
    if INSECURE_SSL:
        print("주의: HTTPS 인증서 검증이 비활성화되어 있습니다(사내 자체서명 대응). 끄려면 INSECURE_SSL=False")
    try:
        ThreadingHTTPServer((host, port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")


if __name__ == "__main__":
    main()
