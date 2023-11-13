# Affluences Reservation System

This Python script helps users make reservations using the Affluences API for their preferred libraries and resources.

## Prerequisites

- Python 3.x
- Affluences API key
- Libraries: `logging`, `requests`, `random`, `json`, `time`, `datetime`, `sys`, `Enum`

## Installation

Clone the repository:

```bash
git clone git@github.com:BIRSAx2/affluences_reservations.git
```

## Configuration

1. Acquire an API key from Affluences.
2. Set up the configuration details in the script:
    - **Library Details**: Identify the specific library IDs.
    - **Resource Preferences**: Set your preferred resources for each library.
    - **User Information**: Add your personal details like email.

## Usage

Run the script using Python:

```bash
python affluences_reservation.py
```

The script will orchestrate the reservation process and make reservations based on the preferences specified in the script.

## Features

- **Reservations by Preferences**: Reserves resources based on user-defined preferences.
- **Flexible Time Slots**: Options to generate different time slot preferences like full-day or half-day reservations.
- **Logging and Error Handling**: Detailed logs are maintained, and error handling is implemented.

## Contribution

1. Fork the repository.
2. Create a new branch.
3. Make your contributions.
4. Commit and push your changes.
5. Create a pull request for review.

## License

This project is licensed under the [MIT License](LICENSE).
