{
    "name": "Auto Attendance Notifications",
    "version": "1.0",
    "category": "Human Resources",
    "summary": "Automatic attendance sending by department",
    "description": "This module allows automating the sending of attendance records based on department configuration.",
    "author": "Ing. Diego Venegas",
    "depends": ["base", "base_setup", "hr", "hr_attendance"],
    "data": [
        "security/ir.model.access.csv",
        "views/auto_attendance_config_view.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": True,
    "assets": {
        "web.assets_backend": [
            "/auto_attendance_notification/static/src/js/*",
            "/auto_attendance_notification/static/src/scss/*",
        ]
    },
}
