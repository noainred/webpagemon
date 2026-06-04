/**
 * WebPageMon 전용 CORS 프록시 — Cloudflare Worker (무료)
 * ---------------------------------------------------------------
 * 공개 프록시(AllOrigins 등)가 막히는 사이트(예: redmir.net)를
 * 감시할 때 사용합니다. 브라우저 User-Agent를 붙여 대상 페이지를
 * 가져오고, CORS 헤더를 추가해 브라우저(WebPageMon)가 읽을 수 있게
 * 그대로 돌려줍니다.
 *
 * ▷ 배포 방법
 *   1. https://dash.cloudflare.com  →  Workers & Pages  →  Create application
 *      →  Create Worker  →  이름 입력(예: webpagemon-proxy)  →  Deploy
 *   2. "Edit code" 를 눌러 이 파일 내용을 전부 붙여넣고  →  Deploy
 *   3. 배포된 주소 확인: https://webpagemon-proxy.<내subdomain>.workers.dev
 *
 * ▷ WebPageMon 앱에서 연결
 *   - 비교 프록시:  직접 입력…
 *   - 사용자 프록시 URL:
 *       https://webpagemon-proxy.<내subdomain>.workers.dev/?url={url}
 *     ({url} 자리표시자를 그대로 두세요. 앱이 감시 대상 주소로 바꿔 넣습니다.)
 *
 * 참고: 대상 사이트가 자바스크립트 챌린지(예: Cloudflare '사람인지 확인')
 * 까지 거는 경우엔 이 단순 프록시로도 통과하지 못할 수 있습니다.
 * 그때는 UA/IP 기반 차단이 아니라는 뜻이며, 헤드리스 브라우저 방식이 필요합니다.
 */

export default {
  async fetch(request) {
    const CORS = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "*",
    };

    // CORS 사전 요청 처리
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }

    const target = new URL(request.url).searchParams.get("url");
    if (!target) {
      return new Response("Missing ?url= parameter", { status: 400, headers: CORS });
    }

    let targetUrl;
    try {
      targetUrl = new URL(target);
    } catch {
      return new Response("Invalid url", { status: 400, headers: CORS });
    }

    // (선택) 오·남용 방지: 특정 도메인만 허용하려면 아래 두 줄의 주석을 해제하세요.
    // const ALLOW = ["www.redmir.net", "redmir.net"];
    // if (!ALLOW.includes(targetUrl.hostname)) return new Response("Host not allowed", { status: 403, headers: CORS });

    try {
      const upstream = await fetch(targetUrl.toString(), {
        method: "GET",
        redirect: "follow",
        headers: {
          // 실제 브라우저처럼 보이게 하는 헤더 (UA 기반 차단 우회 목적)
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
          "Referer": targetUrl.origin + "/",
        },
      });

      const body = await upstream.arrayBuffer();
      const headers = new Headers(CORS);
      const ct = upstream.headers.get("content-type");
      if (ct) headers.set("content-type", ct); // 원본 인코딩(EUC-KR 등) 유지
      // 원 사이트의 상태코드를 그대로 전달 → 200이면 성공, 403 등이면 앱이 오류로 표시
      return new Response(body, { status: upstream.status, headers });
    } catch (e) {
      return new Response("Upstream fetch error: " + (e && e.message), { status: 502, headers: CORS });
    }
  },
};
