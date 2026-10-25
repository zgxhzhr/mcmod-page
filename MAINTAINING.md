# 维护约定

## 发版节奏

**不要每改一次就发版。** 日常改动只 `commit` + `push`；攒到一批（或用户明确说要发版）再打一次 release。

```powershell
git add -A
git commit -F msg.txt          # 多行信息用文件传，见下
git push

# 需要发版时（版本号手动递增）
git archive -o ../mcmod-page-vX.Y.zip --prefix=mcmod-page/ HEAD
gh release create vX.Y ../mcmod-page-vX.Y.zip --title "mcmod-page vX.Y" --notes-file notes.md
```

## 为什么用 `git archive` 而不是压缩文件夹

- 只打包被跟踪的文件，自动排除 `.git`；
- 遵循 `.gitattributes`：`install.sh` 保持 LF（否则 macOS / Linux 上 `bad interpreter`），`*.ps1` 保持 CRLF；
- 不会把 `__pycache__`、生成的 `*.mcmod.html` 带进包里。

## 提交信息的坑

多行提交信息用 `git commit -F 文件`，不要直接 `-m "..."`。命令行里的引号会截断参数，commit 静默失败，随后的 `git archive HEAD` 就会打到上一个（旧的）提交上，发布包里是旧内容。
