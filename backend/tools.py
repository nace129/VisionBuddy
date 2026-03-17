
# tools.py — Agent tools (SOS alert, reminders)

def alert_tool(scene_description: str):
    """Send SOS alert — stub for now"""
    print(f"🚨 SOS ALERT: {scene_description[:100]}")
    return True

def reminder_tool(medication: str):
    """Set medication reminder — stub for now"""
    print(f"⏰ REMINDER SET: {medication}")
    return True