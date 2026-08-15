"""
티스토리 자동 포스팅 v1.0
- 저장된 세션(cookies/{id}_state.json) 사용
- posts/*.json 파일을 읽어 순서대로 발행
- 세션 만료 시 자동 재로그인

posts/ 디렉토리 구조:
  posts/
  └── 001_blogger-parksy.json   ← 파일명 형식 자유
      {
        "account": "dtslib",          ← accounts.json의 id
        "blog":    "blogger-parksy",  ← 블로그 슬러그
        "title":   "제목",
        "content": "<p>본문 HTML</p>",
        "tags":    ["태그1", "태그2"],
        "category": "",               ← 빈 문자열이면 미분류
        "visibility": "public"        ← public | private
      }

실행:
  python3 D:/1_GITHUB/dtslib-papyrus/tools/tistory/post.py
  python3 ... --post posts/001.json   ← 단일 파일
"""

import asyncio, argparse, json, re, time, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE          = Path(__file__).parent
ACCOUNTS_FILE = BASE / "accounts.json"
COOKIES_DIR   = BASE / "cookies"
POSTS_DIR     = BASE / "posts"
LOG_FILE      = BASE / "output" / f"post_{time.strftime('%Y%m%d_%H%M%S')}.log"

COOKIES_DIR.mkdir(exist_ok=True)
POSTS_DIR.mkdir(exist_ok=True)
LOG_FILE.parent.mkdir(exist_ok=True)

LOG_LINES = []
RESULTS   = {"success": [], "fail": []}

def log(msg):
    ts   = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_LINES.append(line)

def save_log():
    LOG_FILE.write_text("\n".join(LOG_LINES), encoding="utf-8")
    log(f"로그 저장: {LOG_FILE}")


# ── 카카오 재로그인 (세션 만료 시) ─────────────────────────
async def kakao_login(page, email, pw):
    log(f"  재로그인: {email}")
    await page.goto("https://www.tistory.com/auth/login",
                    wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    try:
        btn = page.locator("a.btn_login.link_kakao_id, a:has-text('카카오계정으로 로그인')").first
        await btn.wait_for(state="visible", timeout=8000)
        await btn.click()
        await page.wait_for_timeout(4000)
    except Exception as e:
        log(f"  카카오 버튼 없음: {e}")
        return False

    if "kakao.com" in page.url:
        try:
            other = page.locator(
                "a:has-text('다른 계정'), button:has-text('다른 계정'), a:has-text('계정 추가')"
            ).first
            if await other.is_visible(timeout=3000):
                await other.click()
                await page.wait_for_timeout(2000)
        except:
            pass

    try:
        await page.wait_for_selector(
            "#loginId--1, input[name='loginId'], input[autocomplete='username']",
            timeout=15000
        )
        await page.fill("#loginId--1, input[name='loginId'], input[autocomplete='username']", email)
        await page.wait_for_timeout(300)
        await page.fill("#password--2, input[name='password'], input[type='password']", pw)
        await page.wait_for_timeout(300)
        await page.click("button[type='submit'], .btn_g.btn_confirm, button.submit")
        await page.wait_for_timeout(5000)
    except Exception as e:
        log(f"  폼 입력 실패: {e}")

    for _ in range(10):
        url = page.url
        if "tistory.com" in url and "login" not in url and "kakao.com" not in url:
            log("  ✅ 재로그인 성공")
            return True
        await page.wait_for_timeout(1000)

    log(f"  ⚠ 자동 재로그인 실패 — 수동 60초 대기")
    for i in range(60):
        await page.wait_for_timeout(1000)
        url = page.url
        if "tistory.com" in url and "login" not in url and "kakao.com" not in url:
            log(f"  ✅ 수동 재로그인 성공 ({i+1}초)")
            return True

    return False


# ── 로그인 상태 확인 ────────────────────────────────────────
async def _verify_body(page, content: str) -> bool:
    """본문이 제출 소스(textarea#editor-tistory)에 실제로 커밋됐는지 검증 (빵꾸 방지).

    실측: Tistory 는 tinymce.getContent() 가 아니라 textarea#editor-tistory 값을
    제출한다. setContent()는 tinymce 내부 상태만 바꾸고 textarea는 비워둠 →
    editor.save()로 동기화해야 한다. 여기선 textarea 길이를 기준으로 판정."""
    want = len(re.sub(r"<[^>]+>", "", content).strip())
    try:
        got = await page.evaluate("""() => {
            const ed = window.tinymce && tinymce.activeEditor;
            if (!ed) return 0;
            const ta = ed.targetElm || ed.getElement();
            const v = (ta && ta.value) ? ta.value : ed.getContent({format: 'text'}) || '';
            return v.trim().length;
        }""")
    except Exception:
        return False
    return isinstance(got, int) and got >= max(120, int(want * 0.4))


async def _set_category(page, cat: str) -> bool:
    """에디터에서 카테고리 선택.

    메뉴 표시: PART = 'PART N: X' / Ch = '- ChN.M X' (트리 들여쓰기 '- ' 접두어).
    Ch 항목까지 정밀 배치하려면 이 '- ' 접두어를 같이 매칭해야 한다."""
    try:
        await page.locator("#category-btn").click()
        await page.wait_for_timeout(1000)
        sel = (f".mce-menu-item:has(.mce-text:text-is('{cat}')), "
               f".mce-menu-item:has(.mce-text:text-is('- {cat}'))")
        await page.locator(sel).first.click()
        await page.wait_for_timeout(600)
        return True
    except Exception:
        return False


async def _disable_comments(page) -> bool:
    """발행 레이어에서 댓글을 '비허용'으로 강제 설정 (Boss 지시: 매 업로드 댓글 금지).

    댓글 설정은 체크박스가 아니라 TinyMCE select-menu(드롭다운)다.
    '댓글 허용' 버튼 → '댓글 비허용' 메뉴 클릭. _set_category 와 동일 패턴."""
    try:
        await page.locator(".select-menu button.select_btn").filter(has_text="댓글").first.click()
        await page.wait_for_timeout(800)
        await page.locator(".mce-menu-item:has(.mce-text:text-is('댓글 비허용'))").first.click()
        await page.wait_for_timeout(600)
        return True
    except Exception:
        return False


async def ensure_logged_in(page, email, pw):
    # 로그인 여부: TSSESSION(티스토리 세션 쿠키) 존재 확인
    # (tistory.com/manage 는 로그아웃 시 "페이지 없음"만 띄워 URL 로그인 감지가 불가)
    cookies = await page.context.cookies("https://www.tistory.com")
    if any(c["name"] == "TSSESSION" for c in cookies):
        return True
    return await kakao_login(page, email, pw)


# ── 포스트 발행 ─────────────────────────────────────────────
async def _fill_and_save(page, slug: str, post_id: int | None, title: str,
                         content: str, tags: list, cat: str, vis: str) -> bool:
    """신규(post_id=None) 또는 기존 글 수정(post_id 지정) — 에디터 채우고 발행.

    기존 글 수정은 같은 에디터(/manage/newpost/{id}?type=post)를 쓰므로
    제목/본문/카테고리/발행 흐름이 신규와 동일하다. 수정 모드일 땐 기존 제목을
    지우고 다시 타이핑한다. republish.py 가 이 함수를 재사용한다."""
    write_url = (f"https://{slug}.tistory.com/manage/newpost/{post_id}?type=post"
                 if post_id else f"https://{slug}.tistory.com/manage/newpost/?type=post")
    log(f"  [{slug}] 에디터 접근{' (수정)' if post_id else ''}: {write_url}")
    # networkidle/load 모두 불발: 티스토리 편집기는 상시 폴링 + 일부 서브리소스가
    # 영영 안 끝나 load 이벤트가 안 뜬다. DOM 파싱 완료만 기다리는 domcontentloaded
    # 로 대체(서버는 200 정상). 이후 8초 대기 + 타이틀 click()이 액션가능 대기까지 처리.
    await page.goto(write_url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(8000)

    # ── 제목 입력 (실제 타이핑 — React controlled input은 evaluate로 상태 미반영) ──
    try:
        tbox = page.locator("#post-title-inp").first
        await tbox.click()
        if post_id:
            await page.keyboard.press("Control+A")
            await page.wait_for_timeout(150)
        await page.keyboard.type(title, delay=0)
        log(f"  [{slug}] 제목 입력 OK (typing{'/수정' if post_id else ''})")
    except Exception as e:
        log(f"  [{slug}] 제목 타이핑 실패: {e}")

    await page.wait_for_timeout(500)

    # ── 본문 입력 (tinymce setContent + 이벤트 발화 — HTML 렌더 + 상태 반영) ──
    content_filled = False
    try:
        tin_ok = await page.evaluate(
            """(html) => {
                if (window.tinymce && tinymce.activeEditor) {
                    tinymce.activeEditor.setContent(html);
                    tinymce.activeEditor.save();      // ← textarea#editor-tistory 로 강제 동기화 (빵꾸 핵심)
                    tinymce.activeEditor.fire('change');
                    tinymce.activeEditor.fire('input');
                    tinymce.activeEditor.fire('keyup');
                    tinymce.activeEditor.fire('SetContent');
                    return true;
                }
                return false;
            }""",
            content,
        )
        if tin_ok:
            content_filled = True
            log(f"  [{slug}] 본문 입력 OK (tinymce+events)")
    except Exception as e:
        log(f"  [{slug}] tinymce setContent 실패: {e}")

    # 폴백: iframe body 직접
    if not content_filled:
        try:
            body = page.frame_locator("iframe#editor-tistory_ifr").locator("body")
            await body.evaluate(f"el => el.innerHTML = {json.dumps(content)}")
            content_filled = True
            log(f"  [{slug}] 본문 iframe 폴백 OK")
        except:
            pass

    if not content_filled:
        log(f"  [{slug}] 본문 입력 실패 — 스킵")
        RESULTS["fail"].append(f"{slug}:{title[:20]}")
        return False

    # ── 본문 검증 (빵꾸 방지: setContent가 True여도 미커밋되는 레이스 실측) ──
    await page.wait_for_timeout(1500)
    if not await _verify_body(page, content):
        log(f"  [{slug}] 본문 검증 실패 — 재시도")
        try:
            await page.evaluate("""(html) => {
                if (window.tinymce && tinymce.activeEditor) {
                    tinymce.activeEditor.setContent(html);
                    tinymce.activeEditor.save();      // ← textarea 동기화
                    tinymce.activeEditor.fire('change'); tinymce.activeEditor.fire('input');
                }
            }""", content)
            await page.wait_for_timeout(2000)
        except Exception as e:
            log(f"  [{slug}] 재시도 오류: {e}")
    if not await _verify_body(page, content):
        log(f"  [{slug}] 본문 검증 최종 실패 — 스킵 (빵꾸 방지)")
        RESULTS["fail"].append(f"{slug}:{title[:20]}")
        return False

    # ── 카테고리 선택 (PART/Ch 정밀 배치 — category_map SSOT) ──
    if cat:
        ok = await _set_category(page, cat)
        log(f"  [{slug}] 카테고리 설정: {cat}" if ok
            else f"  [{slug}] 카테고리 설정 실패: {cat}")

    await page.wait_for_timeout(500)

    # ── 발행 레이어 열기 (완료 버튼 = #publish-layer-btn) ──
    try:
        await page.locator("#publish-layer-btn").click()
        await page.wait_for_timeout(2000)
        log(f"  [{slug}] 발행 레이어 열림")
    except Exception as e:
        log(f"  [{slug}] 레이어 열기 실패: {e}")

    # ── 공개/비공개 선택 (진짜 클릭 — React state 반영, evaluate로는 안 먹힘) ──
    # basicSet: 20=공개, 15=공개(보호), 0=비공개
    vis_map = {"public": "20", "protected": "15", "private": "0"}
    vis_val = vis_map.get(vis, "20")
    try:
        await page.locator(f"input[name='basicSet'][value='{vis_val}']").check()
        log(f"  [{slug}] 공개 설정: {vis} (value={vis_val})")
    except Exception as e:
        log(f"  [{slug}] 공개 설정 실패: {e}")

    await page.wait_for_timeout(800)

    # ── 댓글 비허용 강제 (Boss 지시: 매 업로드 댓글 금지 — 반드시 적용) ──
    ok_cmt = await _disable_comments(page)
    if ok_cmt:
        log(f"  [{slug}] 댓글 비허용 적용 OK")
    else:
        log(f"  [{slug}] ⚠️ 댓글 비허용 실패 — selector 변경 여부 확인 필요 (발행은 진행)")

    await page.wait_for_timeout(500)

    # ── 발행 버튼 클릭 (공개 선택 시 텍스트 '공개 발행'으로 변경됨) ──
    published = False
    try:
        await page.locator("#publish-btn").click()
        await page.wait_for_timeout(5000)
        # 성공 = 에디터(newpost)를 벗어나 목록/글보기로 이동
        published = "newpost" not in page.url
        if published:
            log(f"  [{slug}] ✅ 발행 완료: {title[:30]}")
            RESULTS["success"].append(f"{slug}:{title[:20]}")
        else:
            log(f"  [{slug}] 발행 후 에디터 유지 — 실패 가능")
    except Exception as e:
        log(f"  [{slug}] 발행 클릭 실패: {e}")

    if not published:
        log(f"  [{slug}] 발행 실패")
        RESULTS["fail"].append(f"{slug}:{title[:20]}")

    return published


async def publish_post(page, post: dict) -> bool:
    """posts/*.json 한 건을 신규 발행한다 (기존 _fill_and_save 의 얇은 래퍼)."""
    return await _fill_and_save(
        page,
        post["blog"],
        None,
        post.get("title", ""),
        post.get("content", ""),
        post.get("tags", []),
        post.get("category", ""),
        post.get("visibility", "public"),
    )


# ── 계정별 처리 ─────────────────────────────────────────────
async def process_account(playwright, acc_id: str, acc_info: dict, posts: list):
    email = acc_info["email"]
    pw    = acc_info["password"]
    log(f"\n{'='*50}\n계정: {email} ({len(posts)}개 포스트)")

    state_path = COOKIES_DIR / f"{acc_id}_state.json"
    ctx_kwargs = dict(
        headless  = True,
        viewport  = {"width": 1280, "height": 900},
        locale    = "ko-KR",
        args      = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
    )

    if state_path.exists():
        ctx = await playwright.chromium.launch_persistent_context(
            str(COOKIES_DIR / acc_id),
            **ctx_kwargs,
        )
    else:
        ctx = await playwright.chromium.launch_persistent_context(
            str(COOKIES_DIR / acc_id),
            **ctx_kwargs,
        )

    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    try:
        ok = await ensure_logged_in(page, email, pw)
        if not ok:
            log(f"  로그인 실패 — 계정 스킵")
            return

        await ctx.storage_state(path=str(state_path))

        for post in posts:
            try:
                await publish_post(page, post)
            except Exception as e:
                slug = post.get("blog", "?")
                title = post.get("title", "?")[:20]
                log(f"  [{slug}] 포스트 오류: {e}")
                RESULTS["fail"].append(f"{slug}:{title}")
            await page.wait_for_timeout(2000)

    except Exception as e:
        log(f"  계정 처리 오류: {e}")
    finally:
        await ctx.close()


# ── 메인 ────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="티스토리 자동 포스팅")
    parser.add_argument("--post", type=str, help="단일 포스트 JSON 파일 경로")
    parser.add_argument("--account", type=str, help="직접 발행: 계정 id (예: galaxys21)")
    parser.add_argument("--title", type=str, help="직접 발행: 제목")
    parser.add_argument("--content", type=str, help="직접 발행: 본문 HTML")
    args = parser.parse_args()

    log("=== 티스토리 자동 포스팅 v1.0 ===")

    data     = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    pw       = data["password"]
    acc_map  = {a["id"]: {**a, "password": pw} for a in data["accounts"]}

    # ── 직접 발행 모드 (--account --title) ──
    if args.account:
        if args.account not in acc_map:
            log(f"❌ 알 수 없는 계정: {args.account}. 가능: {list(acc_map.keys())}")
            sys.exit(1)
        acc = acc_map[args.account]
        blog = acc.get("blog") or args.account
        post = {
            "account": args.account,
            "blog": blog,
            "title": args.title or f"무제 {time.strftime('%Y-%m-%d')}",
            "content": args.content or f"<p>{args.title or '내용 없음'}</p>",
            "tags": [], "category": "", "visibility": "public",
        }
        async with async_playwright() as pw_:
            await process_account(pw_, args.account, acc, [post])
        log(f"\n{'='*50}")
        log(f"성공: {len(RESULTS['success'])}개 → {RESULTS['success']}")
        log(f"실패: {len(RESULTS['fail'])}개 → {RESULTS['fail']}")
        save_log()
        sys.exit(0 if RESULTS["success"] else 1)

    # 포스트 파일 수집
    if args.post:
        post_files = [Path(args.post)]
    else:
        post_files = sorted(POSTS_DIR.glob("*.json"))

    if not post_files:
        log(f"❌ 포스트 파일 없음: {POSTS_DIR}")
        sys.exit(1)

    log(f"포스트 파일: {len(post_files)}개")

    # 계정별로 포스트 그룹화
    acc_posts: dict[str, list] = {}
    for pf in post_files:
        post = json.loads(pf.read_text(encoding="utf-8"))
        acc_id = post.get("account")
        if not acc_id:
            log(f"⚠ 'account' 필드 없음: {pf.name} — 스킵")
            continue
        if acc_id not in acc_map:
            log(f"⚠ 알 수 없는 계정: {acc_id} — 스킵")
            continue
        acc_posts.setdefault(acc_id, []).append(post)

    async with async_playwright() as pw_:
        for acc_id, posts in acc_posts.items():
            await process_account(pw_, acc_id, acc_map[acc_id], posts)
            await asyncio.sleep(3)

    log(f"\n{'='*50}")
    log(f"성공: {len(RESULTS['success'])}개 → {RESULTS['success']}")
    log(f"실패: {len(RESULTS['fail'])}개 → {RESULTS['fail']}")
    save_log()


if __name__ == "__main__":
    asyncio.run(main())
