# Coding Profile Tracker

A web application to track and visualize your competitive programming statistics across multiple platforms (LeetCode, CodeChef, and CodeForces).

## Features

- Track problems solved across platforms
- Visualize problem-solving statistics
- Monitor contest ratings and rankings
- View topic-wise problem distribution
- Real-time data updates
- Clean and modern UI

## Tech Stack

- Backend: Python with FastAPI
- Frontend: HTML, CSS, JavaScript
- Database: SQLite
- Charts: Chart.js
- Icons: Font Awesome

## Setup

1. Clone the repository:
```bash
git clone https://github.com/Vaishnavi063/coding_prof.git
cd coding_prof
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python init_db.py
```

4. Start the server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

5. Open `frontend/profile.html` in your browser to add your coding profiles

## API Endpoints

- POST `/track-profiles`: Add coding profile URLs
- GET `/user/{user_id}/stats`: Get user statistics

## Screenshots

[Add screenshots here]

## Contributing

Feel free to open issues and pull requests for any improvements.

## License

MIT License 