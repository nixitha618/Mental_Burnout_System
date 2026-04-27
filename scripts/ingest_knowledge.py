#!/usr/bin/env python
"""
Script to ingest wellness knowledge into vector database for RAG pipeline
"""

# ===== SQLITE FIX - MUST BE FIRST =====
import sys
import os
import subprocess

try:
    import pysqlite3
    sys.modules['sqlite3'] = pysqlite3
    print("✅ SQLite fix applied")
except ImportError:
    print("⚠️ Installing pysqlite3-binary...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pysqlite3-binary"])
    import pysqlite3
    sys.modules['sqlite3'] = pysqlite3
    print("✅ SQLite fix applied after installation")

import sqlite3
print(f"📊 SQLite version: {sqlite3.sqlite_version}")
# ======================================

# Add project root to path
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import project modules
from src.rag.knowledge_base import KnowledgeBase
from src.utils.logger import setup_logger
from src.utils.helpers import chunk_text

logger = setup_logger(__name__)

# Comprehensive Wellness Knowledge Base
WELLNESS_ARTICLES = [
    {
        "title": "Stress Management Techniques",
        "content": """
        Stress is a common factor in burnout. Here are evidence-based techniques to manage stress:
        
        1. Deep Breathing: Practice the 4-7-8 technique - inhale for 4 seconds, hold for 7, exhale for 8.
        2. Progressive Muscle Relaxation: Tense and relax each muscle group systematically.
        3. Mindfulness Meditation: Spend 10 minutes daily focusing on the present moment.
        4. Regular Exercise: Physical activity releases endorphins and reduces stress hormones.
        5. Social Connection: Talk to friends or family about your feelings.
        6. Time Management: Prioritize tasks and take regular breaks.
        7. Limit Stimulants: Reduce caffeine and alcohol intake.
        8. Nature Exposure: Spend time outdoors to reduce stress levels.
        
        Remember: Chronic stress may require professional support. Consider therapy or counseling.
        """,
        "category": "stress",
        "risk_level": "High"
    },
    {
        "title": "Quick Stress Relief Techniques",
        "content": """
        Immediate stress relief techniques you can use anywhere:
        
        1. Box Breathing: Inhale for 4 seconds, hold for 4, exhale for 4, hold for 4.
        2. Grounding Technique: Name 5 things you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste.
        3. Shoulder Roll: Roll shoulders backward 10 times to release tension.
        4. Hand Massage: Massage pressure points between thumb and index finger.
        5. Drink Water: Dehydration can increase stress hormones.
        6. Change Environment: Step outside or move to a different room.
        7. Listen to Music: Calming music lowers cortisol levels.
        8. Stretch: Stand up and reach for the ceiling for 30 seconds.
        
        These techniques take less than 2 minutes and can be done at your desk.
        """,
        "category": "stress",
        "risk_level": "Medium"
    },
    {
        "title": "Sleep Hygiene Guide",
        "content": """
        Quality sleep is essential for preventing burnout. Follow these sleep hygiene tips:
        
        1. Consistent Schedule: Go to bed and wake up at the same time daily, even on weekends.
        2. Screen-Free Zone: Avoid electronic devices 1 hour before bedtime.
        3. Relaxation Routine: Develop a pre-sleep ritual (reading, gentle stretching, warm bath).
        4. Environment: Keep bedroom cool (65-68°F), dark, and quiet.
        5. Avoid Caffeine: Stop caffeine consumption after 2 PM.
        6. Limit Naps: If you nap, keep it under 30 minutes and before 3 PM.
        7. Regular Exercise: Physical activity promotes better sleep, but not too close to bedtime.
        8. Manage Worries: Write down concerns before bed to clear your mind.
        
        Aim for 7-9 hours of sleep per night for optimal mental wellness.
        """,
        "category": "sleep",
        "risk_level": "Medium"
    },
    {
        "title": "Overcoming Insomnia",
        "content": """
        Strategies for when you can't fall asleep:
        
        1. Get out of bed if you can't sleep after 20 minutes.
        2. Do something relaxing in dim light (read a book, listen to soft music).
        3. Return to bed only when feeling sleepy.
        4. Avoid clock watching - it increases anxiety.
        5. Try the military method: Relax your face, drop shoulders, breathe deeply, clear your mind.
        6. Use white noise or nature sounds to mask disruptive noises.
        7. Ensure your mattress and pillows are comfortable.
        8. Avoid napping during the day if nighttime sleep is poor.
        
        If insomnia persists for more than 2 weeks, consult a healthcare provider.
        """,
        "category": "sleep",
        "risk_level": "High"
    },
    {
        "title": "Work-Life Balance Strategies",
        "content": """
        Maintaining work-life balance prevents burnout. Here are practical strategies:
        
        1. Set Boundaries: Define clear work hours and stick to them.
        2. Learn to Say No: Be realistic about your capacity and decline excessive demands.
        3. Digital Detox: Designate tech-free hours each day.
        4. Prioritize Self-Care: Treat personal time as non-negotiable.
        5. Regular Check-ins: Assess your balance weekly and adjust.
        6. Delegate Tasks: Share responsibilities at work and home.
        7. Take Vacations: Use your time off to truly disconnect.
        8. Pursue Hobbies: Engage in activities unrelated to work.
        9. Quality Time: Be present during personal time without work distractions.
        
        Balance looks different for everyone. Find what works for you and protect it.
        """,
        "category": "workload",
        "risk_level": "Medium"
    },
    {
        "title": "Productivity Techniques for Mental Wellness",
        "content": """
        Sustainable productivity prevents burnout. Try these techniques:
        
        1. Pomodoro Technique: 25 minutes focused work, 5 minutes break.
        2. Eisenhower Matrix: Prioritize tasks by urgency and importance.
        3. MIT Method: Identify 3 Most Important Tasks daily.
        4. Time Blocking: Schedule specific tasks in calendar.
        5. Single-tasking: Focus on one task at a time for better quality.
        6. Regular Breaks: Take short breaks every 90 minutes.
        7. Batch Processing: Group similar tasks together.
        8. Energy Management: Do important tasks during peak energy hours.
        9. Review and Reflect: End each day with a brief review.
        
        Remember: Productivity isn't about doing more, it's about doing what matters.
        """,
        "category": "productivity",
        "risk_level": "Low"
    },
    {
        "title": "Physical Activity for Mental Health",
        "content": """
        Exercise is powerful medicine for mental wellness:
        
        1. Start Small: Even 10-minute walks provide benefits.
        2. Consistency: Aim for 150 minutes moderate activity weekly.
        3. Variety: Mix cardio, strength, and flexibility exercises.
        4. Outdoor Activity: Exercise in nature for added benefits.
        5. Social Exercise: Join group classes or walking groups.
        6. Mindful Movement: Try yoga or tai chi for body-mind connection.
        7. Listen to Your Body: Rest when needed to prevent injury.
        8. Track Progress: Use apps or journals to stay motivated.
        9. Celebrate Small Wins: Acknowledge every effort.
        
        Physical activity releases endorphins, reduces stress, and improves sleep.
        """,
        "category": "exercise",
        "risk_level": "Low"
    },
    {
        "title": "Nutrition for Mental Resilience",
        "content": """
        Diet affects mental wellness significantly:
        
        1. Balanced Meals: Include protein, healthy fats, and complex carbs.
        2. Regular Eating: Don't skip meals, especially breakfast.
        3. Hydration: Drink 8-10 glasses of water daily.
        4. Limit Sugar: Reduce processed foods and sugary drinks.
        5. Omega-3s: Include fatty fish, walnuts, and flaxseeds.
        6. B Vitamins: Found in whole grains, leafy greens, and legumes.
        7. Gut Health: Probiotics and fiber support mood.
        8. Mindful Eating: Pay attention to hunger and fullness cues.
        9. Meal Prep: Plan ahead to avoid unhealthy choices when busy.
        
        Good nutrition provides energy and stabilizes mood throughout the day.
        """,
        "category": "nutrition",
        "risk_level": "Medium"
    },
    {
        "title": "Social Connection and Burnout Prevention",
        "content": """
        Social support is crucial for preventing burnout:
        
        1. Regular Check-ins: Schedule time with friends and family.
        2. Join Communities: Find groups with shared interests.
        3. Quality over Quantity: Focus on meaningful connections.
        4. Be Vulnerable: Share struggles with trusted people.
        5. Offer Support: Helping others reduces isolation.
        6. Set Social Boundaries: Protect time for important relationships.
        7. Digital Connection: Use video calls for long-distance relationships.
        8. Workplace Connections: Build supportive relationships at work.
        9. Seek Professional Support: Therapists and counselors can help.
        
        Humans thrive on connection. Nurture relationships that energize you.
        """,
        "category": "social",
        "risk_level": "High"
    },
    {
        "title": "Mindfulness and Meditation Practices",
        "content": """
        Mindfulness reduces stress and prevents burnout:
        
        1. Breath Awareness: Focus on your breath for 5-10 minutes daily.
        2. Body Scan: Systematically notice sensations throughout your body.
        3. Loving-Kindness: Send well-wishes to yourself and others.
        4. Walking Meditation: Walk slowly and notice each step.
        5. Mindful Eating: Eat without distractions, savoring each bite.
        6. Gratitude Practice: List 3 things you're grateful for daily.
        7. Acceptance: Notice thoughts without judgment.
        8. Apps: Use Headspace, Calm, or Insight Timer for guidance.
        9. Classes: Join local meditation groups or online sessions.
        
        Regular practice rewires the brain for greater resilience and calm.
        """,
        "category": "mindfulness",
        "risk_level": "Low"
    },
    {
        "title": "Recognizing Burnout Warning Signs",
        "content": """
        Early recognition of burnout can prevent crisis. Watch for these signs:
        
        Physical Signs:
        - Chronic fatigue and low energy
        - Frequent headaches or muscle pain
        - Changes in appetite or sleep patterns
        - Weakened immune system (getting sick often)
        
        Emotional Signs:
        - Feeling cynical or negative about work
        - Reduced satisfaction and sense of accomplishment
        - Feeling detached or alone in the world
        - Loss of motivation
        
        Behavioral Signs:
        - Withdrawing from responsibilities
        - Isolating from others
        - Procrastinating
        - Using food, drugs, or alcohol to cope
        
        If you notice multiple signs, take action immediately.
        """,
        "category": "awareness",
        "risk_level": "High"
    },
    {
        "title": "Creating a Self-Care Routine",
        "content": """
        A consistent self-care routine prevents burnout:
        
        Daily Self-Care:
        - Morning: 5 minutes of stretching or meditation
        - During work: Take breaks every 90 minutes
        - Evening: 30 minutes screen-free before bed
        
        Weekly Self-Care:
        - Exercise 3-4 times per week
        - Connect with friends or family
        - Pursue a hobby you enjoy
        
        Monthly Self-Care:
        - Take a full day off for rest
        - Get a massage or spa treatment
        - Review and adjust your goals
        
        Self-care isn't selfish - it's necessary for sustainable wellness.
        """,
        "category": "selfcare",
        "risk_level": "Medium"
    },
    {
        "title": "Anxiety Management Techniques",
        "content": """
        Practical techniques for managing anxiety:
        
        1. 5-4-3-2-1 Grounding: Acknowledge 5 things you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste.
        2. Paper Tiger: Write down your worries, then physically tear up the paper.
        3. Scheduled Worry Time: Set aside 15 minutes daily to worry - postpone anxious thoughts until then.
        4. Cognitive Reframing: Challenge anxious thoughts by asking for evidence.
        5. Progressive Exposure: Gradually face feared situations in small steps.
        6. Relaxation Apps: Use Calm, Headspace, or DARE for guided sessions.
        7. Physical Release: Shake out your hands and arms to release tension.
        8. Count Backwards: Count down from 100 by 7 to distract your mind.
        
        For persistent anxiety, cognitive-behavioral therapy is highly effective.
        """,
        "category": "anxiety",
        "risk_level": "High"
    },
    {
        "title": "Building Mental Resilience",
        "content": """
        Mental resilience helps you bounce back from challenges:
        
        1. Develop a Growth Mindset: View challenges as opportunities to learn.
        2. Build Strong Relationships: Create a support network you can rely on.
        3. Practice Optimism: Focus on what you can control, accept what you can't.
        4. Learn from Failure: Extract lessons from setbacks.
        5. Take Care of Physical Health: Exercise, sleep, and nutrition build resilience.
        6. Find Purpose: Connect daily tasks to larger meaning.
        7. Develop Problem-Solving Skills: Break problems into manageable steps.
        8. Practice Self-Compassion: Treat yourself with kindness during difficult times.
        
        Resilience is like a muscle - it strengthens with practice.
        """,
        "category": "resilience",
        "risk_level": "Low"
    }
]

def ingest_knowledge():
    """Ingest wellness articles into vector database"""
    logger.info("Starting knowledge base ingestion...")
    
    # Initialize knowledge base
    kb = KnowledgeBase()
    
    # Prepare documents
    documents = []
    metadatas = []
    ids = []
    
    for i, article in enumerate(WELLNESS_ARTICLES):
        # Split long articles into chunks
        chunks = chunk_text(article['content'], chunk_size=500)
        
        for j, chunk in enumerate(chunks):
            doc_id = f"{article['category']}_{i}_{j}"
            documents.append(chunk)
            metadatas.append({
                'title': article['title'],
                'category': article['category'],
                'risk_level': article['risk_level'],
                'chunk': j,
                'total_chunks': len(chunks),
                'source': 'wellness_articles'
            })
            ids.append(doc_id)
    
    # Add to knowledge base
    kb.add_documents(documents, metadatas, ids)
    
    # Get stats
    stats = kb.get_stats()
    logger.info(f"Ingestion complete. Stats: {stats}")
    
    return stats

def search_test(query: str, n_results: int = 3):
    """Test search functionality"""
    kb = KnowledgeBase()
    results = kb.search(query, n_results=n_results)
    
    print(f"\n🔍 Search Results for: '{query}'")
    print("="*50)
    
    if results and results['documents'] and results['documents'][0]:
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            similarity = 1 - distance
            print(f"\n--- Result {i+1} (Relevance: {similarity:.2f}) ---")
            print(f"Title: {metadata.get('title', 'N/A')}")
            print(f"Category: {metadata.get('category', 'N/A')}")
            print(f"Risk Level: {metadata.get('risk_level', 'N/A')}")
            print(f"Preview: {doc[:200]}...")
    else:
        print("No results found")
    
    return results

if __name__ == "__main__":
    print("="*60)
    print("📚 KNOWLEDGE BASE INGESTION SCRIPT")
    print("="*60)
    
    try:
        # Ingest all articles
        stats = ingest_knowledge()
        
        print("\n" + "="*60)
        print("✅ INGESTION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\n📊 Statistics:")
        print(f"   Collection: {stats['name']}")
        print(f"   Documents: {stats['document_count']}")
        print(f"   Database Path: {stats['path']}")
        print(f"   SQLite Version: {stats['sqlite_version']}")
        
        # Test searches
        print("\n" + "="*60)
        print("🔍 TESTING SEARCH FUNCTIONALITY")
        print("="*60)
        
        test_queries = [
            "How to manage stress at work?",
            "I can't sleep well at night",
            "Tips for work-life balance",
            "What foods help with mental health?",
            "How to overcome anxiety?"
        ]
        
        for query in test_queries:
            search_test(query, n_results=2)
        
        print("\n" + "="*60)
        print("🎉 KNOWLEDGE BASE IS READY FOR USE!")
        print("="*60)
        print("\nYou can now use the RAG pipeline with:")
        print("  from src.rag.generator import get_generator")
        print("  generator = get_generator(use_gemini=True)")
        print("  result = generator.generate_guidance('Your question here')")
        
    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()