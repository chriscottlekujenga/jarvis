from operations import add, subtract, multiply

def main():
    from operations import divide  # Added import statement for divide
    from flask import Flask, request, jsonify

    app = Flask(__name__)

    while True:
        print("\nSimple Calculator")
        print("1. Add")
        print("2. Subtract")
        print("3. Multiply")
        print("4. Divide")
        print("5. Exit")

        choice = input("Enter your choice (1/2/3/4/5): ")

        if choice == '1':
            num1 = float(input("Enter first number: "))
            num2 = float(input("Enter second number: "))
            result = add(num1, num2)
            print(f"The result of addition is {result}")
        elif choice == '2':
            num1 = float(input("Enter first number: "))
            num2 = float(input("Enter second number: "))
            result = subtract(num1, num2)
            print(f"The result of subtraction is {result}")
        elif choice == '3':
            num1 = float(input("Enter first number: "))
            num2 = float(input("Enter second number: "))
            result = multiply(num1, num2)
            print(f"The result of multiplication is {result}")
        elif choice == '4':
            num1 = float(input("Enter first number: "))
            num2 = float(input("Enter second number: "))
            if num2 != 0:
                result = divide(num1, num2)
                print(f"The result of division is {result}")
            else:
                print("Error: Division by zero")
        elif choice == '5':
            print("Exiting the calculator.")
            break
        else:
            print("Invalid input. Please try again.")
if __name__ == "__main__":
    main()