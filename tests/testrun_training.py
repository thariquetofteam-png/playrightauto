def check_email(varA):
    if "@" in varA and "." in varA:
        return "Valid"
    else:
        return "Invalid"


varb = ["test@gmail.com", "wrongemail", "hello@yahoo.com"]

for varA in varb:
    result = check_email(varA)
    print(f"{varA} --> {result}")