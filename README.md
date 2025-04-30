```
mycroft_voice_control/
│
├── skills/
│   └── smart_home_skill/
│       ├── __init__.py             # Main skill logic
│       ├── settingsmeta.yaml       # Skill configuration
│       ├── vocab/
│       │   ├── en-us/
│       │   │   ├── turn.on.intent
│       │   │   ├── turn.off.intent
│       │   │   ├── set.temp.intent
│       │   │   └── query.status.intent
│       │
│       └── dialog/
│           └── en-us/
│               ├── turned.on.dialog
│               ├── turned.off.dialog
│               └── temperature.set.dialog
│
├── config/
│   └── mycroft.conf                # Mycroft configuration
│
└── start_mycroft.sh                # Launch script
```
# Voice-Gesture-Based-Control
