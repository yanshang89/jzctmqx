import os
from app_web import app, app_state, AUTH_SAVE_PATH, SAVE_CONFIG_PATH, verify_auth
import json

if __name__ == "__main__":
    if os.path.exists(AUTH_SAVE_PATH):
        try:
            with open(AUTH_SAVE_PATH, "r", encoding="utf8") as f:
                saved_code = f.read().strip()
            if saved_code:
                ok, res = verify_auth(saved_code)
                if ok:
                    app_state["auth_pass"] = True
                    app_state["auth_info"] = res
                    print("[系统] 自动授权成功")
        except Exception:
            pass

    if os.path.exists(SAVE_CONFIG_PATH):
        try:
            with open(SAVE_CONFIG_PATH, "r", encoding="utf8") as f:
                cfg = json.load(f)
            app_state["config"].update(cfg)
        except Exception:
            pass

    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
