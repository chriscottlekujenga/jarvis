import random

def main():
    words = ["apple", "banana", "cherry", "date", "elderberry"]
    word_to_guess = random.choice(words)
    guessed_letters = []
    attempts = 6

    print("Welcome to Hangman!")
    while True:
        display_word = ''.join([letter if letter in guessed_letters else '_' for letter in word_to_guess])
        print(f"Word: {display_word}")
        print(f"Attempts left: {attempts}")

        guess = input("Guess a letter (single alphabetic character): ").lower()

        if len(guess) != 1 or not guess.isalpha():
            print("Please enter a single alphabetic character.")
            continue

        if guess in guessed_letters:
            print("You already guessed that letter. Try again.")
            continue

        guessed_letters.append(guess)

        if guess in word_to_guess:
            print("Correct!")
        else:
            attempts -= 1
            print("Incorrect!")

        if set(word_to_guess).issubset(set(guessed_letters)):
            print(f"Congratulations! You won. The word was {word_to_guess}.")
            break

        if attempts == 0:
            print(f"Sorry, you lost. The word was {word_to_guess}.")
            break

    play_again = input("Do you want to play again? (yes/no): ").lower()
    if play_again == 'yes':
        main()

if __name__ == "__main__":
    main()