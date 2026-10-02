import sys
import random
import string
chars = string.ascii_lowercase

with open(sys.argv[1],'r') as f:
 n=f.readline().rstrip()
if n=='random':n = "".join(random.sample(chars, k=5))
for i in range(9):
 g=sys.stdin.readline().rstrip()
 if len(g)!=5:
  print(f'올바르지 않은 입력: {g}',file=sys.stderr);sys.exit(1)
 if len(set(list(g)))!=5:
  print(f'올바르지 않은 입력: {g}',file=sys.stderr);sys.exit(1)
 v=[]
 print('추측: '+g,file=sys.stderr)
 for i in range(5):
  if g[i]==n[i]:v.append('🟩')
  elif g[i] in n:v.append('🟨')
  else:v.append('⬜')
 print(''.join(v),flush=True)
 print(''.join(v),file=sys.stderr)
 if g==n:sys.exit(0)
print(f'실패! 정답은 {n}',file=sys.stderr)
sys.exit(1)

