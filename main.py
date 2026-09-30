import pandas as pd

# ১. দুটি আলাদা ডেমো টার্গেটের CDR ডাটা তৈরি
target1_data = {
    'A_Party': ['8801700000000'] * 4,
    'B_Party': ['8801811111111', '8801922222222', '8801633333333', '8801811111111'],
    'Call_Date': ['2026-09-29'] * 4
}

target2_data = {
    'A_Party': ['8801800000000'] * 4,
    'B_Party': ['8801811111111', '8801544444444', '8801922222222', '8801555555555'],
    'Call_Date': ['2026-09-29'] * 4
}

df1 = pd.DataFrame(target1_data)
df2 = pd.DataFrame(target2_data)

# ২. দুটি টার্গেটের B_Party (প্রাপক) থেকে কমন নম্বরগুলো খুঁজে বের করা
target1_contacts = set(df1['B_Party'])
target2_contacts = set(df2['B_Party'])

common_numbers = target1_contacts.intersection(target2_contacts)

print("=========================================")
print("    COMMON CONTACTS REPORT (কমন নম্বর)   ")
print("=========================================\n")

print(f"Target 1-এর মোট ইউনিক যোগাযোগ: {len(target1_contacts)} টি")
print(f"Target 2-এর মোট ইউনিক যোগাযোগ: {len(target2_contacts)} টি\n")

print("উভয় টার্গেটের সাথে যোগাযোগ থাকা কমন নম্বরসমূহ:")
for num in common_numbers:
    t1_calls = len(df1[df1['B_Party'] == num])
    t2_calls = len(df2[df2['B_Party'] == num])
    print(f" ➔ নম্বর: {num} (Target 1 এর সাথে {t1_calls} বার, Target 2 এর সাথে {t2_calls} বার কথা হয়েছে)")