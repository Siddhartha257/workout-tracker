# Fitness Tracker - User Authentication System

A comprehensive fitness tracking web application with user authentication, workout logging, and diet tracking capabilities.

## 🚀 Features

### Authentication System
- **User Registration**: Complete signup form with user profile information
- **Secure Login**: JWT-based authentication with password hashing
- **Session Management**: Persistent login with localStorage
- **Logout Functionality**: Secure session termination

### Workout Tracking
- **Exercise Logging**: Log workouts with muscle groups, exercise types, and sets
- **Workout History**: View and manage past workouts
- **AI Suggestions**: Get personalized workout recommendations
- **CRUD Operations**: Create, read, update, and delete workout entries

### Diet Tracking
- **Nutrition Logging**: Log food items with automatic nutrition calculation
- **Meal Categorization**: Organize entries by meal type (breakfast, lunch, dinner, snack)
- **Nutrition Summary**: View daily nutrition totals
- **AI Diet Suggestions**: Get personalized nutrition advice

### Security Features
- **Password Hashing**: Secure password storage using bcrypt
- **JWT Tokens**: Stateless authentication with token expiration
- **User Isolation**: Each user can only access their own data
- **Input Validation**: Comprehensive form validation and sanitization

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fitness_tracker
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   cd app
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the application**
   - Open your browser and navigate to `http://localhost:8000`
   - Start with the signup page: `http://localhost:8000/signup.html`

## 📁 Project Structure

```
fitness_tracker/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── routes/
│   │   ├── db.py           # Database models and configuration
│   │   ├── user.py         # User authentication routes
│   │   ├── workouts.py     # Workout management routes
│   │   └── diet.py         # Diet tracking routes
│   ├── templates/
│   │   ├── login.html      # Login page
│   │   ├── signup.html     # User registration page
│   │   ├── workouts.html   # Workout tracking interface
│   │   └── diet.html       # Diet tracking interface
│   └── workouts.db         # SQLite database
├── requirements.txt         # Python dependencies
└── README.md              # This file
```

## 🔧 API Endpoints

### Authentication
- `POST /signup` - User registration
- `POST /login` - User login
- `POST /logout` - User logout
- `GET /me` - Get current user info

### Workouts
- `POST /workout` - Create new workout
- `GET /workouts` - Get user's workout history
- `GET /workout/{id}` - Get specific workout
- `PUT /workout/{id}` - Update workout
- `DELETE /workout/{id}` - Delete workout
- `GET /ai-suggestions` - Get AI workout suggestions

### Diet
- `POST /diet` - Create diet entry
- `GET /diet` - Get today's diet entries
- `GET /diet/{date}` - Get diet entries by date
- `PUT /diet/{id}` - Update diet entry
- `DELETE /diet/{id}` - Delete diet entry
- `GET /diet/summary/{start_date}/{end_date}` - Get nutrition summary
- `POST /diet/suggestions` - Get AI diet suggestions

## 🎯 Usage Guide

### Getting Started
1. **Create an Account**: Visit the signup page and fill in your profile information
2. **Login**: Use your credentials to access the application
3. **Start Tracking**: Begin logging your workouts and diet entries

### Workout Tracking
1. **Add Workout**: Select muscle group, exercise type, and add sets
2. **View History**: Browse your workout history by date
3. **Edit/Delete**: Modify or remove existing workouts
4. **AI Suggestions**: Get personalized workout recommendations

### Diet Tracking
1. **Log Meals**: Add food items with quantities
2. **View Summary**: See daily nutrition totals
3. **Track Progress**: Monitor your nutrition over time
4. **Get Advice**: Receive AI-powered diet suggestions

## 🔒 Security Features

- **Password Security**: Passwords are hashed using bcrypt
- **JWT Authentication**: Secure token-based authentication
- **User Isolation**: Data is completely isolated per user
- **Input Validation**: All inputs are validated and sanitized
- **Session Management**: Automatic token expiration and renewal

## 🎨 UI Features

- **Modern Design**: Dark theme with Bootstrap 5
- **Responsive Layout**: Works on desktop and mobile devices
- **Real-time Updates**: Dynamic content updates without page refresh
- **User Feedback**: Toast notifications for user actions
- **Navigation**: Easy navigation between workout and diet sections

## 🚀 Deployment

### Local Development
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Deployment
1. Set environment variables for production
2. Use a production WSGI server like Gunicorn
3. Configure a reverse proxy (nginx)
4. Set up SSL certificates
5. Use a production database (PostgreSQL/MySQL)

## 🔧 Configuration

### Environment Variables
- `SECRET_KEY`: JWT secret key (change in production)
- `DATABASE_URL`: Database connection string
- `GEMINI_API_KEY`: Google Gemini API key for AI features

### Database
The application uses SQLite by default. For production, consider using PostgreSQL or MySQL.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For support or questions, please open an issue in the repository.

---

**Note**: This application is for educational and personal use. For production deployment, ensure proper security measures are implemented. 