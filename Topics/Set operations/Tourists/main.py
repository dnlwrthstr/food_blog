# work with these variables
eugene = set(input().split())
rose = set(input().split())

print(eugene - rose | rose - eugene)
#  print(eugene.symmetric_difference(rose))
#  print(eugene ^ rose)
