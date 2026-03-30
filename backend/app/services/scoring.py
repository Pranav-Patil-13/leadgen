import json
from typing import Dict, Any, List, Tuple

def calculate_lead_score(lead_data: Dict[str, Any]) -> Tuple[int, str, List[str]]:
    """
    Calculates a lead score (0-100) and identifies opportunity tags.
    Returns: (score, score_label, opportunity_tags)
    """
    score = 25  # Base score for being discovered
    tags = []
    
    # 1. Website Analysis
    website = lead_data.get("website")
    if website:
        score += 15
    else:
        tags.append("No Website")
        
    # 2. Rating Analysis
    rating_str = lead_data.get("rating")
    try:
        rating = float(rating_str) if rating_str else 0
        if rating >= 4.5:
            score += 20
        elif rating >= 3.5:
            score += 10
        elif rating > 0 and rating < 3.0:
            score += 5
            tags.append("Needs Reviews")
    except (ValueError, TypeError):
        pass
        
    # 3. Contact Analysis
    if lead_data.get("email"):
        score += 15
    else:
        tags.append("Missing Email")
        
    if lead_data.get("phone"):
        score += 15
    else:
        tags.append("No Phone Num")
        
    # 4. Social Presence Analysis
    social_links_str = lead_data.get("social_links")
    if social_links_str:
        try:
            socials = json.loads(social_links_str)
            if len(socials) > 0:
                score += 10
            else:
                tags.append("No Socials")
        except:
            tags.append("No Socials")
    else:
        tags.append("No Socials")

    # 5. Intent/Urgency Analysis (for Social/Student Leads)
    intent_data = lead_data.get("intent_data")
    if intent_data:
        intent_lower = intent_data.lower()
        
        # High Urgency Keywords
        urgency_keywords = ["urgent", "deadline", "tomorrow", "days left", "help me", "immediately"]
        if any(word in intent_lower for word in urgency_keywords):
            score += 30
            tags.append("High Urgency")
            
        # Buying Intent Keywords
        buying_keywords = ["hire", "paid", "freelancer", "buy", "purchase", "budget", "price"]
        if any(word in intent_lower for word in buying_keywords):
            score += 25
            tags.append("Commercial Intent")
            
        # Technical Confusion (Opportunity for service)
        confusion_keywords = ["stuck", "confused", "how to start", "error", "debug", "implementation"]
        if any(word in intent_lower for word in confusion_keywords):
            score += 15
            tags.append("Needs Guidance")

    # Determine Label
    label = "Low"
    if score >= 85: # Increased threshold for High because of new point potential
        label = "High"
    elif score >= 55:
        label = "Medium"
        
    return min(score, 100), label, tags
