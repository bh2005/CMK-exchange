# Example Ticket System Configurations
# Copy one of these to: ~/etc/check_mk/multisite.d/wato/ticket_system.mk

# =============================================================================
# ZAMMAD CONFIGURATION
# =============================================================================
"""
# Zammad Ticket System
ticket_system_config = {
    'enabled': True,
    'system_type': 'zammad',
    'url': 'https://zammad.example.com',
    'api_token': 'your-zammad-api-token-here',
    'api_endpoint': '/api/v1/tickets',
    'show_stats': True,
    'show_links': True,
    'verify_ssl': True,
}

# How to get Zammad API Token:
# 1. Login to Zammad
# 2. Go to Profile → Token Access
# 3. Click "Create"
# 4. Copy token and paste above
"""

# =============================================================================
# GLPI CONFIGURATION
# =============================================================================
"""
# GLPI Ticket System
ticket_system_config = {
    'enabled': True,
    'system_type': 'glpi',
    'url': 'https://glpi.example.com',
    'api_token': 'your-glpi-user-token',
    'api_endpoint': '/apirest.php/Ticket',
    'show_stats': True,
    'show_links': True,
    'verify_ssl': True,
}

# How to get GLPI API Token:
# 1. Login to GLPI
# 2. Go to Setup → General → API
# 3. Enable REST API
# 4. Go to User → API Tokens
# 5. Generate token
"""

# =============================================================================
# JIRA CONFIGURATION
# =============================================================================
"""
# Jira Ticket System
ticket_system_config = {
    'enabled': True,
    'system_type': 'jira',
    'url': 'https://jira.example.com',
    'username': 'automation@example.com',
    'password': 'jira-api-token-not-actual-password',
    'api_endpoint': '/rest/api/2/search',
    'show_stats': True,
    'show_links': True,
    'verify_ssl': True,
}

# How to get Jira API Token:
# 1. Login to Jira
# 2. Go to Account Settings → Security → API Tokens
# 3. Click "Create API token"
# 4. Copy token and use as 'password' above
"""

# =============================================================================
# CUSTOM/GENERIC REST API
# =============================================================================
"""
# Custom Ticket System with REST API
ticket_system_config = {
    'enabled': True,
    'system_type': 'custom',
    'url': 'https://tickets.example.com',
    'api_token': 'your-api-token',
    'api_endpoint': '/api/tickets',
    'show_stats': True,
    'show_links': True,
    'verify_ssl': True,
}

# Expected API Response format:
# GET {url}{api_endpoint}/stats should return:
# {
#   "new": 5,
#   "open": 12,
#   "pending": 3,
#   "closed": 45,
#   "total": 65
# }
"""

# =============================================================================
# DISABLED CONFIGURATION (Default)
# =============================================================================
"""
# Ticket System Disabled
ticket_system_config = {
    'enabled': False,
    'system_type': 'custom',
    'url': '',
    'api_token': '',
    'show_stats': True,
    'show_links': True,
    'verify_ssl': True,
}
"""
