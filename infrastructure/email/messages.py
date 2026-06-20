"""Plain-language email errors for admins and end users."""


def normalize_email(value: str) -> str:
    return (value or '').strip().lower()


def friendly_email_send_error(exc: Exception) -> str:
    """Turn SMTP/network exceptions into short, non-technical guidance."""
    text = str(exc).lower()

    if any(token in text for token in ('errno 8', 'nodename', 'gaierror', 'name or service not known')):
        return (
            'We could not reach the email service. '
            'Check that this computer has internet access, then share the login details below with the student.'
        )
    if any(token in text for token in ('authentication', '535', '534', 'username and password not accepted')):
        return (
            'The school email account is not set up correctly on the server. '
            'Share the login details below with the student until email is fixed.'
        )
    if 'timed out' in text or 'timeout' in text:
        return (
            'The email service did not respond in time. '
            'The account was still created — share the login details below with the student.'
        )
    if '550' in text or '553' in text or 'address not found' in text or 'user unknown' in text:
        return (
            'That email address could not receive mail (it may be misspelled or inactive). '
            'Double-check the address, or share the login details below with the student another way.'
        )
    return (
        'The welcome email could not be sent. '
        'The account was still created — share the login details below with the student.'
    )


def friendly_validation_message(message: str) -> str:
    """Map internal validation text to admin-friendly wording."""
    mapping = {
        'email and role are required': 'Please enter an email address and choose Student or Teacher.',
        'Email is already registered': (
            'This email is already used by another account. '
            'Use a different email or edit the existing user.'
        ),
        'Username must be at most 7 characters': 'Username must be 7 letters or fewer.',
        'Username is already taken': 'That username is already taken. Leave username blank to auto-generate one.',
        'Invalid teacher selected': 'Please choose a valid teacher from the list.',
        'Cannot create admin accounts via API': 'Admin accounts cannot be created from this screen.',
    }
    return mapping.get(message, message)
