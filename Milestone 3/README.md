# Employee Wellness Management Analytics

## Milestone 3 – Emotion Detection & Journal Analytics

### Project Objective

Develop an AI-powered journal module that analyzes employee journal entries using multilingual NLP, transformer-based emotion detection, and VADER sentiment analysis. The processed results are securely stored in a PostgreSQL database and displayed through the frontend.

---

## Model Used

* Hugging Face Transformer Model (Emotion Detection)
* VADER Sentiment Analyzer
* PyTorch

---

## Emotion Detection Pipeline

**Journal Entry → NLP Preprocessing → Language Detection → Emotion Detection → Confidence Score → Sentiment Analysis → Database Storage → Frontend Display**

---

## Confidence Score

The confidence score is the highest prediction probability returned by the transformer model for the detected emotion. It indicates the model's confidence in its prediction and is stored along with the journal entry.

---

## Sentiment Analysis

VADER computes the following sentiment scores:

* Positive Score
* Negative Score
* Neutral Score
* Compound Score

The compound score represents the overall sentiment polarity and is stored in the database.

---

## Database Schema

Each journal record stores:

* User ID
* Journal Text
* Detected Language
* Predicted Emotion
* Confidence Score
* Positive Score
* Negative Score
* Neutral Score
* Compound Sentiment Score
* Timestamp

---

## API Endpoints

* **POST** `/emotion/predict`
* **POST** `/sentiment/analyze`
* **POST** `/journal/add`
* **GET** `/journal/history`

---

## Sample Input & Output

### Input

```
Today I completed all my work and feel motivated.
```

### Output

```
Language: English
Emotion: Joy
Confidence: 94%
Positive Score: 0.68
Negative Score: 0.03
Neutral Score: 0.29
Compound Sentiment: 0.91
```

---

## Observations

* Successfully integrated multilingual NLP with transformer-based emotion detection.
* Implemented confidence score calculation for emotion predictions.
* VADER sentiment analysis complements emotion prediction by providing detailed sentiment scores.
* Journal entries and analysis results are securely stored in PostgreSQL.
* The frontend displays language, emotion, confidence score, sentiment scores, and journal history for users.
