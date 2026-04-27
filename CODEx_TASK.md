项目目标：
基于 sailors_onboard-main 中已实现的小车能力，在 openclaw_lab_adapter 中封装为 skills。

工作原则：
1. openclaw_lab_adapter 是唯一允许修改的主项目。
2. sailors_onboard-main 仅作参考，不直接修改。
3. 优先提炼能力边界、输入输出、调用方式，再封装 skill。
4. 生成的代码需便于后续接入 OpenClaw / Sailors Onboard skill 系统。
5. 修改代码之前，先向我询问是否开始修改，向我申请需要修改的代码文件，预期效果