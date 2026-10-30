"""Short fictional demo knowledge checks; they do not replace local practical training."""


COURSES = {
    'introductory 3d printer safety': {
        'pass_mark': 80,
        'lesson': [
            'Demo lesson only. Before operating real equipment, read the facility procedure and complete instructor-led hands-on training.',
            'Follow the manufacturer instructions and the institution’s local rules for materials, ventilation and protective equipment.',
            'Keep clear of hot and moving parts. Never bypass guards or safety controls.',
            'Stop and contact the instructor if the equipment behaves unexpectedly, is damaged, or you are unsure what to do.',
        ],
        'questions': [
            {'prompt': 'Before using the printer, what should you do?', 'options': ['Follow the facility procedure and instructor guidance', 'Start it and learn as you go', 'Disable any control that slows the job'], 'answer': 0},
            {'prompt': 'You notice damage or unexpected behavior. What is the safest response?', 'options': ['Keep working carefully', 'Stop and contact the instructor', 'Try to repair it without telling anyone'], 'answer': 1},
            {'prompt': 'May you bypass a guard or safety control to clear a problem?', 'options': ['Yes, if the job is almost done', 'Only when no one is watching', 'No'], 'answer': 2},
            {'prompt': 'Which materials and protective equipment should you use?', 'options': ['Whatever is nearby', 'Those approved by the facility procedure and instructor', 'No protective equipment is ever needed'], 'answer': 1},
            {'prompt': 'When may you approach hot or moving parts?', 'options': ['Only as directed by the instructor and equipment procedure', 'Whenever the printer looks quiet', 'While it is running, if you are quick'], 'answer': 0},
        ],
    },
    'robotics lab orientation': {
        'pass_mark': 80,
        'lesson': [
            'Demo lesson only. Complete the real lab orientation and supervised practice before operating robotics equipment.',
            'Follow the instructor’s procedure for power isolation before changing wiring or working near moving parts.',
            'Keep people and loose items outside the robot’s movement area. Know where the local stop control is before a test.',
            'Stop a test and alert the instructor if movement is unexpected, a component is damaged, or the work area is unclear.',
        ],
        'questions': [
            {'prompt': 'Before changing wiring, what should you do?', 'options': ['Follow the instructor’s power-isolation procedure', 'Leave power on to save time', 'Ask another student to hold the wires'], 'answer': 0},
            {'prompt': 'A robot moves unexpectedly during a test. What should you do?', 'options': ['Reach in and grab it', 'Stop the test using the taught procedure and alert the instructor', 'Continue and record a video'], 'answer': 1},
            {'prompt': 'When is it okay to bypass a safety control?', 'options': ['When the test is short', 'When the robot is small', 'It is not okay'], 'answer': 2},
            {'prompt': 'What should be true before a movement test?', 'options': ['The area is clear and the instructor’s procedure is followed', 'Someone stands beside the moving parts', 'The stop control is hidden'], 'answer': 0},
            {'prompt': 'What should you do if you are unsure about a setup?', 'options': ['Guess based on a previous project', 'Pause and ask the instructor', 'Copy a setup from the internet'], 'answer': 1},
        ],
    },
    'electrical workshop safety': {
        'pass_mark': 80,
        'lesson': [
            'Demo lesson only. This quiz is not an electrical qualification. Complete the institution’s supervised practical training before using workshop equipment.',
            'Follow the instructor’s procedure for making equipment safe before wiring or changing a circuit.',
            'Use only equipment and protective measures approved for the task. Do not open mains-powered equipment unless specifically qualified and authorised.',
            'Stop and report damaged insulation, unexpected heat, sparks, or any situation you do not understand.',
        ],
        'questions': [
            {'prompt': 'Before changing a circuit, what should you do?', 'options': ['Follow the instructor’s safe-isolation procedure', 'Work quickly while it is powered', 'Ask someone to touch the wires first'], 'answer': 0},
            {'prompt': 'You find damaged insulation. What should you do?', 'options': ['Cover it temporarily and continue', 'Stop using it and tell the instructor', 'Test it with your hand'], 'answer': 1},
            {'prompt': 'May you open mains-powered equipment without authorisation?', 'options': ['Yes, if you have a screwdriver', 'Only after watching a video', 'No'], 'answer': 2},
            {'prompt': 'Which instruments should you use?', 'options': ['Any instrument that fits', 'Only equipment rated and approved for the task', 'A damaged instrument if readings appear normal'], 'answer': 1},
            {'prompt': 'If the task or setup is unclear, what is the safe choice?', 'options': ['Pause and ask the instructor', 'Guess and continue', 'Ask an untrained visitor'], 'answer': 0},
        ],
    },
}


def course_for(title):
    key=' '.join((title or '').casefold().split())
    return COURSES.get(key)
