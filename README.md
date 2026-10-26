# skills

个人使用的 Agent Skills。本仓库内的技能以各自目录为唯一维护源，安装目录只放软链接；后续修改直接提交到本仓库。

## 技能

- [vlog-skill](vlog-skill/SKILL.md)：旅行 Vlog 剪辑、局部改版、声音诊断与封面制作。

## 安装

将下面的 `xx` 换成技能名（如 `vlog-skill`），发送给 Agent：

```text
帮我安装 https://github.com/FayeSpica/skills 中的 xx skill。优先复用本地已有仓库，没有则克隆一份。以仓库中的技能目录为唯一维护源，在 ~/.agents/skills/xx 创建软链接，不复制技能文件。若已有同名入口，先核对内容与指向，保留本地修改，确认内容一致后再迁移，最终只保留一个安装入口。完成后验证 SKILL.md 及其引用文件可读，并告知仓库位置和软链接指向。
```
