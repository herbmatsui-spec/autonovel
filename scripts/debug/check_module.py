import sys
sys.path.insert(0, 'E:\\hhh')

import src.services.marketing as sm
print("Attributes in src.services.marketing:", [attr for attr in dir(sm) if not attr.startswith('_')])
print("Has MarketingAgent?", hasattr(sm, 'MarketingAgent'))
if hasattr(sm, 'MarketingAgent'):
    print("MarketingAgent class:", sm.MarketingAgent)
    print("Module:", sm.MarketingAgent.__module__)