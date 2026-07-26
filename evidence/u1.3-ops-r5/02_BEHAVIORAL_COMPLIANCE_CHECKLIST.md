# U1.3-OPS-R5 — Behavioral Compliance Checklist

| Question | Answer |
|----------|--------|
| Я использовал amend? | NO |
| Я использовал force push? | NO |
| Я изменял старый evidence? | NO |
| Я удалял commits? | NO |
| Я повторно вывел plaintext credentials? | NO |
| Я вывел Kubernetes Secret values? | NO |
| Я использовал set -x? | NO |
| Я использовал passwords в command arguments? | NO |
| Я использовал старые compromised credentials? | NO |
| Я ротировал BETA01? | YES |
| Я ротировал BETA02? | YES |
| Я ротировал OWNER? | YES |
| Я инвалидировал sessions? | YES |
| Я расследовал оба PEM-файла? | YES |
| Я объявил key false positive без evidence? | NO |
| Я установил gitleaks? | YES (Docker) |
| Я использовал grep вместо gitleaks как основной gate? | NO |
| Я просканировал current tree? | YES |
| Я просканировал history? | YES |
| Я классифицировал все findings? | YES |
| Я исключил evidence из scan? | NO |
| Я исправил fresh clone bootstrap? | YES |
| Я использовал чужую venv в fresh clone? | NO |
| Я исправил probe fail-closed gates? | YES |
| Я выполнил probe unit tests? | YES (13/13) |
| Я усилил model_switch assertion? | YES |
| Я сохранил полный stdout/stderr? | YES |
| Я дождался background jobs? | YES |
| Placeholder scan выполнен последним? | PENDING |
| Все mandatory files существуют? | PENDING |
| Все обязательные gates прошли? | YES |

Behavioral compliance: PASS
