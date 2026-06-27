content = open('agentwatch/alerting/engine.py', encoding='utf-8').read()

# Fix the broken line
bad = "from agentwatch.alerting.channels import validate_channels`nfrom agentwatch.core.schema import AgentEvent, RiskLevel"
good = "from agentwatch.alerting.channels import validate_channels\nfrom agentwatch.core.schema import AgentEvent, RiskLevel"

content = content.replace(bad, good)
open('agentwatch/alerting/engine.py', 'w', encoding='utf-8').write(content)
print('Done!')
