# Frameflow Skill

A project-neutral **video-production workflow skill plus offline evidence CLI**.
It helps a human or a capable assistant carry a brief through story, directing,
assets, animation, editing, sound, independent review, repair and delivery.
It is not a video generator, renderer, hosted service or artistic scoring engine.
No original production assets, voices, account information or private integrations
are included. No adoption, maturity or application acceptance is claimed.

## Start (Python 3.10+, standard library only)

Run from this folder. No installation, credentials or network access is needed.

```sh
python -m frameflow validate examples/demo/manifest.json
python -m frameflow verify examples/demo/manifest.json
python -m frameflow next examples/demo/manifest.json
python -m unittest discover -s tests -v
```

`examples/review/manifest.json` is a second, review-only fixture with an original
SVG card; it remains unreviewed and cannot request a generation action.

The planning example is deliberately unfinished and synthetic: a paper kite story outline,
not an actual rendered or reviewed film. `next` reports its first pending action.
Use `SKILL.md` as workflow guidance in an assistant that supports skills; actual
creative tools and their permissions remain your responsibility. Start a project
from `templates/workflow.md`, explicitly choose tools and review requirements,
then track locally available artifacts in a manifest matching the example.

## Commands and honest boundaries

- `validate`: exact-field schema, mode allowlist, required stage coverage, IDs,
  dependencies, review coverage, evidence bindings. Does **not** read evidence.
- `verify`: all validation checks plus current artifact/evidence bytes.
- `next`: verification plus the first unresolved recorded obligation.

Failed reviews are reported without requesting edits in review-only mode;
only revise/production mode can advise a repair. Changing a recorded result
invalidates its scope binding and requires truthful replacement evidence.

All declared actions and reviews are required; optional checks belong outside
this minimum manifest until adopted. Multiple obligations per stage are allowed.
`plan` requires brief/story/director; `review` requires review only;
`revise` and `production` require all nine stages. Non-applicable production stages
need an honest documented no-op decision, not an invented executed output.
Every artifact in non-plan mode must have explicit review coverage.

Completion is only `RECORDED_OBLIGATIONS_COMPLETE`, never a film-quality pass.
Review identities are labels, not authenticated identities. A hash proves byte
identity, not truth, perception, provenance, permission or review independence.
You must map every actual task requirement into obligations: the checker cannot
infer omitted user requirements or enforce an external standard it was not given.
Do not downgrade mode or edit away obligations to simulate completion.

See [architecture](docs/architecture.md), [security](SECURITY.md),
[adapter contracts](docs/adapters.md) and [contributing](CONTRIBUTING.md).

## 中文说明

这是尚未公开的初版：通用视频制作工作流 Skill + 本地证据检查工具，
不是自动制片平台，不包含原项目素材、音色、账号或私有接口。
工作流覆盖策划、故事、导演、资产、动画、剪辑、声音、独立审查与交付；
工具只验证结构、文件哈希和已登记义务，不能证明艺术质量或真实独立审查。
模型、供应商、语言、风格、预算及权限由各项目自行配置。
运行上方四条命令即可检查纯合成示例及测试。采用 MIT 许可证；当前发行包已准备，远端发布状态须以实际仓库为准。

## License and release status

Original code and documentation are provided under the [MIT License](LICENSE).
This initial package is **prepared for release**; this document does not claim
that a remote repository, package-index release or application submission exists.
See [release notes](RELEASE.md). No third-party production assets are included.
