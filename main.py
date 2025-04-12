from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from sqlalchemy.orm import Session
import asyncio
from requests.exceptions import Timeout, RequestException
import traceback
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from models import get_db, UserProfile, LeetCodeStats, CodeChefStats, CodeForcesStats

app = FastAPI(title="Profile Tracker API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProfileURLs(BaseModel):
    leetcode_url: Optional[str] = None
    codechef_url: Optional[str] = None
    codeforces_url: Optional[str] = None

class ProblemStats(BaseModel):
    total_solved: int
    platform_breakdown: Dict[str, int]
    difficulty_breakdown: Dict[str, int]

@app.get("/")
async def root():
    return {"message": "Welcome to Profile Tracker API"}

@app.post("/track-profiles")
async def track_profiles(profiles: ProfileURLs, db: Session = Depends(get_db)):
    try:
        logger.info("Received profile tracking request")
        
        # Check if profile already exists with any of these URLs
        existing_profile = None
        if profiles.leetcode_url:
            existing_profile = db.query(UserProfile).filter(UserProfile.leetcode_url == profiles.leetcode_url).first()
        if not existing_profile and profiles.codechef_url:
            existing_profile = db.query(UserProfile).filter(UserProfile.codechef_url == profiles.codechef_url).first()
        if not existing_profile and profiles.codeforces_url:
            existing_profile = db.query(UserProfile).filter(UserProfile.codeforces_url == profiles.codeforces_url).first()

        if existing_profile:
            logger.info(f"Updating existing profile with ID: {existing_profile.id}")
            # Update existing profile
            if profiles.leetcode_url:
                existing_profile.leetcode_url = profiles.leetcode_url
            if profiles.codechef_url:
                existing_profile.codechef_url = profiles.codechef_url
            if profiles.codeforces_url:
                existing_profile.codeforces_url = profiles.codeforces_url
            existing_profile.updated_at = datetime.utcnow()
            db.commit()
            user_profile = existing_profile
        else:
            logger.info("Creating new user profile")
            # Create new profile
            user_profile = UserProfile(
                leetcode_url=profiles.leetcode_url or "",
                codechef_url=profiles.codechef_url or "",
                codeforces_url=profiles.codeforces_url or ""
            )
            db.add(user_profile)
            db.commit()
            db.refresh(user_profile)
            logger.info(f"Created user profile with ID: {user_profile.id}")
        
        # Create tasks for each platform
        tasks = []
        if profiles.leetcode_url:
            tasks.append(fetch_leetcode_stats(user_profile.id, profiles.leetcode_url, db))
        if profiles.codechef_url:
            tasks.append(fetch_codechef_stats(user_profile.id, profiles.codechef_url, db))
        if profiles.codeforces_url:
            tasks.append(fetch_codeforces_stats(user_profile.id, profiles.codeforces_url, db))
        
        if tasks:
            try:
                logger.info("Starting to fetch platform stats")
                await asyncio.wait_for(asyncio.gather(*tasks), timeout=30)
                logger.info("Successfully fetched all platform stats")
            except asyncio.TimeoutError:
                logger.warning("Some requests timed out")
                return {
                    "message": "Profiles partially tracked (some requests timed out)",
                    "user_id": user_profile.id,
                    "status": "partial"
                }
            except Exception as e:
                logger.error(f"Error during stats fetching: {str(e)}")
                logger.error(traceback.format_exc())
                return {
                    "message": "Profiles partially tracked (some errors occurred)",
                    "user_id": user_profile.id,
                    "status": "partial"
                }
        
        return {
            "message": "Profiles tracked successfully",
            "user_id": user_profile.id,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Unexpected error in track_profiles: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{user_id}/stats")
async def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    try:
        # Fetch latest stats from each platform
        leetcode_stats = db.query(LeetCodeStats).filter(
            LeetCodeStats.user_id == user_id
        ).order_by(LeetCodeStats.recorded_at.desc()).first()
        
        codechef_stats = db.query(CodeChefStats).filter(
            CodeChefStats.user_id == user_id
        ).order_by(CodeChefStats.recorded_at.desc()).first()
        
        codeforces_stats = db.query(CodeForcesStats).filter(
            CodeForcesStats.user_id == user_id
        ).order_by(CodeForcesStats.recorded_at.desc()).first()
        
        total_solved = (
            (leetcode_stats.total_problems_solved if leetcode_stats else 0) +
            (codechef_stats.total_problems_solved if codechef_stats else 0) +
            (codeforces_stats.total_problems_solved if codeforces_stats else 0)
        )
        
        return {
            "total_problems_solved": total_solved,
            "platform_stats": {
                "leetcode": {
                    "total_solved": leetcode_stats.total_problems_solved if leetcode_stats else 0,
                    "easy_solved": leetcode_stats.easy_solved if leetcode_stats else 0,
                    "medium_solved": leetcode_stats.medium_solved if leetcode_stats else 0,
                    "hard_solved": leetcode_stats.hard_solved if leetcode_stats else 0,
                    "contest_rating": leetcode_stats.contest_rating if leetcode_stats else None,
                    "contests_participated": leetcode_stats.contests_participated if leetcode_stats else 0
                },
                "codechef": {
                    "total_solved": codechef_stats.total_problems_solved if codechef_stats else 0,
                    "rating": codechef_stats.contest_rating if codechef_stats else None,
                    "highest_rating": codechef_stats.highest_rating if codechef_stats else None,
                    "contests_participated": codechef_stats.contests_participated if codechef_stats else 0,
                    "categories": codechef_stats.problem_categories if codechef_stats else {}
                },
                "codeforces": {
                    "total_solved": codeforces_stats.total_problems_solved if codeforces_stats else 0,
                    "rating": codeforces_stats.contest_rating if codeforces_stats else None,
                    "rank": codeforces_stats.rank if codeforces_stats else None,
                    "contests_participated": codeforces_stats.contests_participated if codeforces_stats else 0,
                    "problem_tags": codeforces_stats.problem_tags if codeforces_stats else {}
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def fetch_leetcode_stats(user_id: int, leetcode_url: str, db: Session):
    try:
        # Skip if URL is empty
        if not leetcode_url:
            print("LeetCode URL is empty, skipping")
            return

        # Extract username from URL and clean it
        username = leetcode_url.strip('/').split('/')[-1]
        # Handle both formats: /u/username and /username
        if username == 'u':
            username = leetcode_url.strip('/').split('/')[-2]
            
        if not username:
            print("Invalid LeetCode URL format")
            return

        print(f"Fetching LeetCode stats for user: {username}")
        
        # Use GraphQL API for more accurate data
        url = "https://leetcode.com/graphql"
        query = """
        query getUserProfile($username: String!) {
            matchedUser(username: $username) {
                username
                submitStats: submitStatsGlobal {
                    acSubmissionNum {
                        difficulty
                        count
                    }
                }
            }
        }
        """
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.post(
            url,
            json={
                'query': query,
                'variables': {'username': username}
            },
            headers=headers,
            timeout=10
        )
        
        # Check response status
        if response.status_code != 200:
            print(f"LeetCode API returned status code: {response.status_code}")
            print(f"Response content: {response.text}")
            return
            
        data = response.json()
        print(f"LeetCode API Response: {json.dumps(data, indent=2)}")

        if 'errors' in data:
            print(f"LeetCode API error: {data['errors']}")
            return

        user_data = data.get('data', {}).get('matchedUser')
        if not user_data:
            print(f"No data found for user: {username}")
            return

        # Get submission stats
        submit_stats = user_data.get('submitStats', {}).get('acSubmissionNum', [])
        
        # Calculate problems by difficulty
        easy_solved = 0
        medium_solved = 0
        hard_solved = 0
        
        for stat in submit_stats:
            difficulty = stat.get('difficulty')
            count = stat.get('count', 0)
            if difficulty == 'Easy':
                easy_solved = count
            elif difficulty == 'Medium':
                medium_solved = count
            elif difficulty == 'Hard':
                hard_solved = count
        
        total_solved = easy_solved + medium_solved + hard_solved
        
        print(f"Found stats for {username}:")
        print(f"Total solved: {total_solved}")
        print(f"Easy: {easy_solved}")
        print(f"Medium: {medium_solved}")
        print(f"Hard: {hard_solved}")
        
        # Create new stats record
        stats = LeetCodeStats(
            user_id=user_id,
            total_problems_solved=total_solved,
            easy_solved=easy_solved,
            medium_solved=medium_solved,
            hard_solved=hard_solved,
            contests_participated=0,
            contest_rating=None,
            global_rank=0
        )
        
        db.add(stats)
        db.commit()
        print(f"Successfully saved LeetCode stats for {username}")
        
    except Timeout:
        print(f"Timeout while fetching LeetCode stats for {username}")
    except RequestException as e:
        print(f"Network error while fetching LeetCode stats: {str(e)}")
    except Exception as e:
        print(f"Error fetching LeetCode stats: {str(e)}")
        print(traceback.format_exc())
        
    return None

async def fetch_codechef_stats(user_id: int, codechef_url: str, db: Session):
    try:
        # Skip if URL is empty
        if not codechef_url:
            print("CodeChef URL is empty, skipping")
            return

        # Extract username from URL and clean it
        username = codechef_url.split('/')[-1].strip('/')
        if not username:
            print("Invalid CodeChef URL format")
            return

        print(f"Fetching CodeChef stats for user: {username}")
        
        # Headers to mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

        # Get the user profile page
        profile_url = f"https://www.codechef.com/users/{username}"
        response = requests.get(
            profile_url,
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"CodeChef returned status code: {response.status_code}")
            return
            
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get current rating
        rating_header = soup.find('div', class_='rating-header')
        current_rating = None
        highest_rating = None
        if rating_header:
            rating_number = rating_header.find('div', class_='rating-number')
            if rating_number:
                current_rating = float(rating_number.text.strip())
            
            # Get highest rating
            highest_rating_div = rating_header.find('div', class_='rating-star')
            if highest_rating_div:
                highest_text = highest_rating_div.get_text(strip=True)
                try:
                    highest_rating = float(''.join(filter(str.isdigit, highest_text)))
                except:
                    pass

        # Get problem counts
        problems_solved = 0
        problem_categories = {}
        
        # Find the problems solved section
        problems_section = soup.find('section', {'class': 'rating-data-section problems-solved'})
        if problems_section:
            # Count fully solved problems
            fully_solved_header = problems_section.find('h5', string='Fully Solved')
            if fully_solved_header:
                problems_list = fully_solved_header.find_next('article')
                if problems_list:
                    problems = problems_list.find_all('p')
                    problems_solved = len(problems)
                    
                    # Categorize problems
                    for problem in problems:
                        problem_text = problem.get_text(strip=True)
                        category = 'practice'  # Default category
                        if '(Challenge)' in problem_text:
                            category = 'challenge'
                        elif '(Contest)' in problem_text:
                            category = 'contest'
                        problem_categories[category] = problem_categories.get(category, 0) + 1

        # Get contest participation
        contests_participated = 0
        contest_section = soup.find('section', {'class': 'rating-data-section contests-attended'})
        if contest_section:
            contests_list = contest_section.find_all('p')
            contests_participated = len(contests_list)

        print(f"Found stats for {username}:")
        print(f"Current Rating: {current_rating}")
        print(f"Highest Rating: {highest_rating}")
        print(f"Problems Solved: {problems_solved}")
        print(f"Contests Participated: {contests_participated}")
        print(f"Problem Categories: {problem_categories}")
        
        # Create new stats record
        stats = CodeChefStats(
            user_id=user_id,
            total_problems_solved=problems_solved,
            contest_rating=current_rating,
            highest_rating=highest_rating,
            contests_participated=contests_participated,
            problem_categories=problem_categories
        )
        
        db.add(stats)
        db.commit()
        print(f"Successfully saved CodeChef stats for {username}")
        
    except Timeout:
        print(f"Timeout while fetching CodeChef stats for {username}")
    except RequestException as e:
        print(f"Network error while fetching CodeChef stats: {str(e)}")
    except Exception as e:
        print(f"Error fetching CodeChef stats: {str(e)}")
        print(traceback.format_exc())
        
    return None

async def fetch_codeforces_stats(user_id: int, codeforces_url: str, db: Session):
    try:
        # Skip if URL is empty
        if not codeforces_url:
            print("CodeForces URL is empty, skipping")
            return

        # Extract handle from URL and clean it
        handle = codeforces_url.split('/')[-1].strip('/')
        if not handle:
            print("Invalid CodeForces URL format")
            return

        print(f"Fetching CodeForces stats for user: {handle}")
        
        # Get user info
        user_info_url = f"https://codeforces.com/api/user.info?handles={handle}"
        submissions_url = f"https://codeforces.com/api/user.status?handle={handle}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Get user info
        user_response = requests.get(user_info_url, headers=headers, timeout=10)
        if user_response.status_code != 200:
            print(f"CodeForces API returned status code: {user_response.status_code}")
            return
            
        user_data = user_response.json()
        print(f"CodeForces User API Response: {json.dumps(user_data, indent=2)}")
        
        if user_data['status'] != 'OK':
            print(f"CodeForces API error: {user_data.get('comment', 'Unknown error')}")
            return
            
        user_info = user_data['result'][0]
        
        # Get submissions
        submissions_response = requests.get(submissions_url, headers=headers, timeout=10)
        if submissions_response.status_code != 200:
            print(f"CodeForces Submissions API returned status code: {submissions_response.status_code}")
            return
            
        submissions_data = submissions_response.json()
        print(f"CodeForces Submissions API Response: {json.dumps(submissions_data, indent=2)}")
        
        if submissions_data['status'] != 'OK':
            print(f"CodeForces Submissions API error: {submissions_data.get('comment', 'Unknown error')}")
            return
        
        # Count unique solved problems and categorize by tags
        solved_problems = set()
        problem_tags = {}
        
        for submission in submissions_data['result']:
            if submission['verdict'] == 'OK':
                problem = submission['problem']
                problem_id = f"{problem.get('contestId', '')}{problem.get('index', '')}"
                
                if problem_id not in solved_problems:
                    solved_problems.add(problem_id)
                    # Count problem tags
                    for tag in problem.get('tags', []):
                        problem_tags[tag] = problem_tags.get(tag, 0) + 1
        
        total_solved = len(solved_problems)
        
        print(f"Found stats for {handle}:")
        print(f"Total solved: {total_solved}")
        print(f"Rating: {user_info.get('rating', 'Not rated')}")
        print(f"Max Rating: {user_info.get('maxRating', 'Not rated')}")
        print(f"Rank: {user_info.get('rank', 'Not ranked')}")
        print(f"Problem tags: {problem_tags}")
        
        # Create new stats record
        stats = CodeForcesStats(
            user_id=user_id,
            total_problems_solved=total_solved,
            contest_rating=user_info.get('rating'),
            highest_rating=user_info.get('maxRating'),
            rank=user_info.get('rank', 'newbie'),
            contests_participated=user_info.get('maxRank', 0),
            problem_tags=problem_tags
        )
        
        db.add(stats)
        db.commit()
        print(f"Successfully saved CodeForces stats for {handle}")
        
    except Timeout:
        print(f"Timeout while fetching CodeForces stats for {handle}")
    except RequestException as e:
        print(f"Network error while fetching CodeForces stats: {str(e)}")
    except Exception as e:
        print(f"Error fetching CodeForces stats: {str(e)}")
        print(traceback.format_exc())
        
    return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 