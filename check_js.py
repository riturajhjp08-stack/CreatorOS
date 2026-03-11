import re
with open("app.html", "r") as f:
    html = f.read()
scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
with open("temp.js", "w") as f:
    f.write(scripts[0])
