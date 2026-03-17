import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_offline_downloads.py", "tests/test_feature_parity.py", "-v", "--tb=short"],
    cwd=r"C:\Users\Simon\PycharmProjects\hometools",
    capture_output=True,
    text=True
)

print(result.stdout)
print(result.stderr)

