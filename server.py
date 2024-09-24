import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

allowed_locations = ["Albuquerque, New Mexico", "Carlsbad, California", "Chula Vista, California",
    "Colorado Springs, Colorado", "Denver, Colorado", "El Cajon, California","El Paso, Texas", 
    "Escondido, California", "Fresno, California", "La Mesa, California", "Las Vegas, Nevada", 
    "Los Angeles, California", "Oceanside, California", "Phoenix, Arizona", "Sacramento, California",
    "Salt Lake City, Utah", "San Diego, California", "Tucson, Arizona"
]

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def filter_reviews(self, location: str = None, start_date: str = None, end_date: str = None) -> list:
        filtered_reviews = []

        for review in reviews:
            review_location = review["Location"]
            review_timestamp = datetime.strptime(review["Timestamp"], '%Y-%m-%d %H:%M:%S')

            if location and review_location != location:
                continue
            
            if start_date:
                start_date_dt = datetime.strptime(start_date,'%Y-%m-%d')
                if review_timestamp < start_date_dt:
                    continue

            if end_date:
                end_date_dt = datetime.strptime(end_date,'%Y-%m-%d')
                if review_timestamp > end_date_dt:
                    continue

            review['sentiment'] = self.analyze_sentiment(review['ReviewBody'])
            filtered_reviews.append(review)

        filtered_reviews.sort(key=lambda x: x['sentiment']['compound'], reverse=True)
        return filtered_reviews

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string
            query_params = parse_qs(environ["QUERY_STRING"])
            location = query_params.get("location", [None])[0]
            start_date = query_params.get("start_date", [None])[0]
            end_date = query_params.get("end_date", [None])[0]

            if location and location not in allowed_locations:
                response_body = json.dumps({"error": "Location not allowed"}).encode("utf-8")
                start_response("400 Bad Request", [("Content-Type","application/json"),("Content-Length", str(len(response_body)))])
                return [response_body]
            
            filtered_reviews = self.filter_reviews(location,start_date,end_date)
            response_body = json.dumps(filtered_reviews, indent=2).encode("utf-8")
            
            # Write your code here
            

            # Set the appropriate response headers
            start_response("200 OK", [("Content-Type", "application/json"),("Content-Length", str(len(response_body)))])
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            # Write your code here
            try:
                content_length = int(environ.get('CONTENT_LENGTH',0))
                body = environ['wsgi.input'].read(content_length).decode('utf-8')
                post_params = parse_qs(body)

                review_body = post_params.get("ReviewBody",[None])[0]
                location = post_params.get("Location", [None])[0]

                if not review_body or not location:
                    response_body = json.dumps({"error": "ReviewBody and Location are required."}).encode("utf-8")
                    start_response("400 Bad Request", [("Content-Type", "application/json"),("Content-Length", str(len(response_body)))])
                    return [response_body]
                
                if location not in allowed_locations:
                    response_body = json.dumps({"error": "Location not allowed."}).encode("utf-8")
                    start_response("400 Bad Request", [("Content-Type", "application/json"),("Content-Length", str(len(response_body)))])
                    return [response_body]
                
                new_review = {
                    "ReviewId": str(uuid.uuid4()),
                    "ReviewBody": review_body,
                    "Location": location,
                    "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                reviews.append(new_review)
                response_body = json.dumps(new_review, indent=2).encode("utf-8")
                start_response("201 Created", [("Content-Type","application/json"),("Content-Length", str(len(response_body)))])
                return [response_body]
            
            except Exception as e:
                response_body = json.dumps({"error": str(e)}).encode("utf-8")
                start_response("500 Internal Server Error", [("Content-Type","application/json"), ("Content-Length", str(len(response_body)))])
                return [response_body]

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()