# skills

个人使用的 Agent Skills。本仓库内的技能以各自目录为唯一维护源，安装目录只放软链接；后续修改直接提交到本仓库。

## 技能

- [vlog-skill](vlog-skill/SKILL.md)：旅行 Vlog 剪辑、局部改版、声音诊断与封面制作。

## 本地安装

在仓库根目录执行，沿用当前 Codex 的个人技能入口：

```sh
mkdir -p "$HOME/.codex/skills"
ln -s "$PWD/vlog-skill" "$HOME/.codex/skills/vlog-skill"
```

若入口已经存在，先检查它的类型和指向，避免覆盖尚未迁入仓库的内容。不要在安装目录另外维护副本，也不要在多个技能扫描目录重复安装同名入口。

[OpenAI 官方说明](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)确认 Codex 支持软链接技能目录。新环境采用文档所列的 `~/.agents/skills/` 时，将上面的安装目录替换为该路径即可。
