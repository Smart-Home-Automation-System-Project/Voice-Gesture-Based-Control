def parse_rhasspy_intent(intent_name):
    """
    Parses a Rhasspy intent name and maps it to a device name and state.
    Returns a dictionary like {"name": "device", "state": "action"} or None if no mapping exists.
    """
    if intent_name == "Light1_On":
        return {"name": "l1", "state": "on"}
    elif intent_name == "Light1_Off":
        return {"name": "l1", "state": "off"}
    elif intent_name == "Light2_On":
        return {"name": "l2", "state": "on"}
    elif intent_name == "Light2_Off":
        return {"name": "l2", "state": "off"}
    elif intent_name == "Light3_On":
        return {"name": "l3", "state": "on"}
    elif intent_name == "Light3_Off":
        return {"name": "l3", "state": "off"}
    elif intent_name == "Light4_On":
        return {"name": "l4", "state": "on"}
    elif intent_name == "Light4_Off":
        return {"name": "l4", "state": "off"}
    elif intent_name == "Light5_On":
        return {"name": "l5", "state": "on"}
    elif intent_name == "Light5_Off":
        return {"name": "l5", "state": "off"}
    elif intent_name == "Light6_On":
        return {"name": "l6", "state": "on"}
    elif intent_name == "Light6_Off":
        return {"name": "l6", "state": "off"}
    elif intent_name == "Light7_On":
        return {"name": "l7", "state": "on"}
    elif intent_name == "Light7_Off":
        return {"name": "l7", "state": "off"}
    elif intent_name == "Light8_On":
        return {"name": "l8", "state": "on"}
    elif intent_name == "Light8_Off":
        return {"name": "l8", "state": "off"}
    elif intent_name == "FrontDoor_Open":
        return {"name": "front_door", "state": "unlock"}
    elif intent_name == "FrontDoor_Close":
        return {"name": "front_door", "state": "lock"}
    elif intent_name == "BackDoor_Open":
        return {"name": "back_door", "state": "unlock"}
    elif intent_name == "BackDoor_Close":
        return {"name": "back_door", "state": "lock"}
    elif intent_name == "Gate_Open":
        return {"name": "gate", "state": "unlock"}
    elif intent_name == "Gate_Close":
        return {"name": "gate", "state": "lock"}
    elif intent_name == "LivingRoomTV_On":
        return {"name": "living_room_tv", "state": "on"}
    elif intent_name == "LivingRoomTV_Off":
        return {"name": "living_room_tv", "state": "off"}
    elif intent_name == "WashingMachine_On":
        return {"name": "washing_machine", "state": "on"}
    elif intent_name == "WashingMachine_Off":
        return {"name": "washing_machine", "state": "off"}
    elif intent_name == "VacuumCleaner_On":
        return {"name": "vacuum_cleaner", "state": "on"}
    elif intent_name == "VacuumCleaner_Off":
        return {"name": "vacuum_cleaner", "state": "off"}
    elif intent_name == "Refrigerator_On":
        return {"name": "refrigerator", "state": "on"}
    elif intent_name == "Refrigerator_Off":
        return {"name": "refrigerator", "state": "off"}
    elif intent_name == "Microwave_On":
        return {"name": "microwave", "state": "on"}
    elif intent_name == "Microwave_Off":
        return {"name": "microwave", "state": "off"}
    elif intent_name == "Dishwasher_On":
        return {"name": "dishwasher", "state": "on"}
    elif intent_name == "Dishwasher_Off":
        return {"name": "dishwasher", "state": "off"}
    # Add any other specific mappings here if needed
    else:
        # If the intent_name doesn't match any predefined mapping
        print(f"Warning: Intent '{intent_name}' has no custom payload mapping.")
        return None