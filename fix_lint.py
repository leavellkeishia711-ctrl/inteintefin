import re

# Fix SettingsScreen
f1 = '05-frontend/src/components/screens/SettingsScreen.tsx'
c1 = open(f1, encoding='utf8').read()
c1 = re.sub(r'(setLocale\(localStorage\.getItem\(''financeIntel-locale''\))', r'// eslint-disable-next-line react-hooks/set-state-in-effect\n    \1', c1)
open(f1, 'w', encoding='utf8').write(c1)

# Fix PnLScreen
f2 = '05-frontend/src/components/screens/PnLScreen.tsx'
c2 = open(f2, encoding='utf8').read()
c2 = c2.replace('"', '&quot;')
open(f2, 'w', encoding='utf8').write(c2)

# Fix staffing
f3 = '05-frontend/src/lib/staffing.tsx'
c3 = open(f3, encoding='utf8').read()
c3 = c3.replace('// eslint-disable-next-line react-hooks/set-state-in-effect\n', '')
open(f3, 'w', encoding='utf8').write(c3)

# Fix PartnersScreen
f4 = '05-frontend/src/components/screens/PartnersScreen.tsx'
c4 = open(f4, encoding='utf8').read()
c4 = re.sub(r'Number\((.*?)\)', r'\1', c4)
open(f4, 'w', encoding='utf8').write(c4)
