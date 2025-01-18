def hw1():
    txt = """ James, while John had had "had", had had "had had";
 "had had" had had a better effect on the teacher."""
    x = txt.count("had")
    print(x)

def hw2():
    numberofletters = " Pneumonoultramicroscopicsilicovolcanoconiosis"
    x = len(numberofletters)
    print (x)
def hw3():
    first_name = input ("what is your first name: ")
    last_name = input ("what is your surname: ")
    greet = f"Hello, {first_name.capitalize()} {last_name.upper()}!"
    print(greet)

def hw4():
    INCH_TO_CENTIMERTER = 2.54
    size_in_inches= input("how large is your tv screen in inches: ")
    size_in_inches = float(size_in_inches)
    size_in_centimeters = size_in_inches * INCH_TO_CENTIMERTER
    print (size_in_centimeters)
def hw5():
    height_in_feet = float(input ("what is your height in feet "))
    height_in_added_inches = float(input ("what is the amount of added inches needed "))
    height_in_centimeters = ((height_in_feet * 12 ) +height_in_added_inches ) * 2.54
    print (height_in_centimeters)
def hw5ext():
    INCH_TO_CENTIMERTER = 2.54
    height_in_centimeters = float(input("what is your height in cm: "))
    height_in_inches = height_in_centimeters / 2.54
    height_in_feet = height_in_inches // 12
    rem_in_inches = height_in_inches % 12
    print (f"your height is {height_in_feet}feet and {rem_in_inches}inches ")
def hw6():
    base = float(input("who long is the base?: "))
    height = float(input("what is the height?: "))
    area = base * height / 2
    print (f"the area is {area}")

if __name__ == "__main__":
    hw6()


