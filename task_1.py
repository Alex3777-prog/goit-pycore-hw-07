import re
from collections import UserDict
from datetime import date, datetime, timedelta
from functools import wraps


DATE_FORMAT = "%d.%m.%Y"
UPCOMING_DAYS = 7


class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    def __init__(self, value: str):
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty.")
        super().__init__(value)


class Phone(Field):
    def __init__(self, value: str):
        if not re.fullmatch(r"[0-9]{10}", value):
            raise ValueError("Phone number must contain exactly 10 digits.")
        super().__init__(value)


class Birthday(Field):
    def __init__(self, value: str):
        try:
            birthday = datetime.strptime(value, DATE_FORMAT)
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY") from None
        if birthday > datetime.today():
            raise ValueError("Birthday cannot be in the future.")
        super().__init__(birthday)

    def __str__(self):
        return self.value.strftime(DATE_FORMAT)


class Record:
    def __init__(self, name: str):
        self.name = Name(name)
        self.phones: list[Phone] = []
        self.birthday: Birthday | None = None

    def add_phone(self, phone: str) -> None:
        if self.find_phone(phone):
            raise ValueError("This phone number already exists.")
        self.phones.append(Phone(phone))

    def find_phone(self, phone: str) -> Phone | None:
        return next((p for p in self.phones if p.value == phone), None)

    def remove_phone(self, phone: str) -> None:
        found = self.find_phone(phone)
        if found:
            self.phones.remove(found)

    def edit_phone(self, old_phone: str, new_phone: str) -> None:
        found = self.find_phone(old_phone)
        if found is None:
            raise ValueError("Phone not found.")
        if new_phone != old_phone and self.find_phone(new_phone):
            raise ValueError("This phone number already exists.")
        self.phones[self.phones.index(found)] = Phone(new_phone)

    def add_birthday(self, birthday: str) -> None:
        self.birthday = Birthday(birthday)

    def __str__(self):
        phones = "; ".join(p.value for p in self.phones)
        birthday = self.birthday or "not specified"
        return (
            f"Contact name: {self.name.value}, "
            f"phones: {phones}, birthday: {birthday}"
        )


class AddressBook(UserDict):
    def add_record(self, record: Record) -> None:
        self.data[record.name.value] = record

    def find(self, name: str) -> Record | None:
        return self.data.get(name)

    def delete(self, name: str) -> None:
        self.data.pop(name, None)

    def get_upcoming_birthdays(self) -> list[dict[str, str]]:
        today = date.today()
        upcoming = []

        for record in self.data.values():
            if record.birthday is None:
                continue

            birthday = record.birthday.value.date()
            next_birthday = self._next_birthday(birthday, today)
            if (next_birthday - today).days >= UPCOMING_DAYS:
                continue

            greeting_date = self._shift_to_weekday(next_birthday)
            upcoming.append(
                {
                    "name": record.name.value,
                    "congratulation_date": greeting_date.strftime(DATE_FORMAT),
                }
            )

        return upcoming

    @staticmethod
    def _birthday_in_year(birthday: date, year: int) -> date:
        try:
            return birthday.replace(year=year)
        except ValueError:  # 29.02 in a non-leap year
            return birthday.replace(year=year, day=28)

    @classmethod
    def _next_birthday(cls, birthday: date, today: date) -> date:
        next_birthday = cls._birthday_in_year(birthday, today.year)
        if next_birthday < today:
            next_birthday = cls._birthday_in_year(birthday, today.year + 1)
        return next_birthday

    @staticmethod
    def _shift_to_weekday(day: date) -> date:
        """Move Saturday and Sunday to the following Monday."""
        if day.weekday() >= 5:
            return day + timedelta(days=7 - day.weekday())
        return day


def input_error(func):
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as error:
            return str(error)
        except IndexError:
            return "Enter user name."
        except KeyError:
            return "Contact not found."

    return inner


def parse_input(user_input: str) -> tuple[str, ...]:
    parts = user_input.split()
    if not parts:
        return ("",)
    command, *args = parts
    return command.lower(), *args


def get_record(book: AddressBook, name: str) -> Record:
    """Return the contact or raise KeyError for input_error to report."""
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    return record


@input_error
def add_contact(args: list[str], book: AddressBook) -> str:
    if len(args) < 2:
        raise ValueError("Please provide a name and phone number.")

    name, phone, *_ = args
    record = book.find(name)
    if record is None:
        record = Record(name)
        record.add_phone(phone)
        book.add_record(record)
        return "Contact added."

    record.add_phone(phone)
    return "Contact updated."


@input_error
def change_contact(args: list[str], book: AddressBook) -> str:
    if len(args) != 3:
        raise ValueError("Please provide a name, old phone and new phone.")

    name, old_phone, new_phone = args
    get_record(book, name).edit_phone(old_phone, new_phone)
    return "Contact updated."


@input_error
def show_phone(args: list[str], book: AddressBook) -> str:
    record = get_record(book, args[0])
    phones = "; ".join(p.value for p in record.phones)
    return f"{record.name.value}: {phones}"


def show_all(book: AddressBook) -> str:
    if not book:
        return "No contacts."
    return "\n".join(str(record) for record in book.values())


@input_error
def add_birthday(args: list[str], book: AddressBook) -> str:
    if len(args) < 2:
        raise ValueError(
            "Please provide a contact name and birthday (DD.MM.YYYY)."
        )

    name, birthday, *_ = args
    record = get_record(book, name)
    message = "Birthday updated." if record.birthday else "Birthday added."
    record.add_birthday(birthday)
    return message


@input_error
def show_birthday(args: list[str], book: AddressBook) -> str:
    record = get_record(book, args[0])
    if record.birthday is None:
        return "Birthday not specified."
    return f"{record.name.value}: {record.birthday}"


@input_error
def birthdays(args: list[str], book: AddressBook) -> str:
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No upcoming birthdays."
    return "\n".join(
        f"{user['name']}: {user['congratulation_date']}" for user in upcoming
    )


def main() -> None:
    book = AddressBook()
    print("Welcome to the assistant bot!")

    while True:
        try:
            user_input = input("Enter a command: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGood bye!")
            break

        command, *args = parse_input(user_input)

        if command in ("close", "exit"):
            print("Good bye!")
            break
        elif command == "hello":
            print("How can I help you?")
        elif command == "add":
            print(add_contact(args, book))
        elif command == "change":
            print(change_contact(args, book))
        elif command == "phone":
            print(show_phone(args, book))
        elif command == "all":
            print(show_all(book))
        elif command == "add-birthday":
            print(add_birthday(args, book))
        elif command == "show-birthday":
            print(show_birthday(args, book))
        elif command == "birthdays":
            print(birthdays(args, book))
        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()
