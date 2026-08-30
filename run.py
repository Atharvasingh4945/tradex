import os
import sys

# Ensure current directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Ensure UTF-8 output in Windows terminal
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    from app import create_app
except ImportError:
    from tradex.app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5055))
    print("\n=======================================================")
    print(f"  TradeX Terminal & Behavioral Journal is Running!")
    print(f"  URL: http://127.0.0.1:{port}")
    print(f"  Demo Login: trader@tradex.com | Password: tradex123")
    print("=======================================================\n")
    app.run(host='127.0.0.1', port=port, debug=False)
