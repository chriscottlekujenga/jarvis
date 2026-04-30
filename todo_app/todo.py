# todo.py

tasks = []
completed_tasks = []

def add_task(task):
    tasks.append(task)
    print(f"Task added: {task}")

def list_tasks():
    if not tasks:
        print("No tasks to display.")
    else:
        print("Tasks:")
        for index, task in enumerate(tasks, start=1):
            print(f"{index}. {task}")

def mark_task_complete(task_index):
    try:
        task = tasks.pop(task_index - 1)
        completed_tasks.append(task)
        print(f"Task marked as complete: {task}")
    except IndexError:
        print("Invalid task index.")

def main_menu():
    while True:
        print("\nTo-Do List Application")
        print("1. Add Task")
        print("2. List Tasks")
        print("3. Mark Task Complete")
        print("4. Exit")
        
        choice = input("Enter your choice: ")
        
        if choice == '1':
            task = input("Enter the task to add: ")
            add_task(task)
        elif choice == '2':
            list_tasks()
        elif choice == '3':
            task_index = int(input("Enter the task number to mark as complete: "))
            mark_task_complete(task_index)
        elif choice == '4':
            print("Exiting the application.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main_menu()