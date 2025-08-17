"""
Demo responses for showcasing the application without LLM costs.
These responses demonstrate various features and response types.
"""

DEMO_RESPONSES = {
    "sales": {
        "how many sales": {
            "response": "Found 2,847 sales order records in the database.",
            "mode": "text"
        },
        "sales today": {
            "response": "Retrieved 145 sales orders for today.",
            "mode": "text"
        },
        "top products": {
            "response": "SELECT product_name, SUM(quantity) as total_sold FROM sales_orders GROUP BY product_name ORDER BY total_sold DESC LIMIT 10",
            "mode": "table"
        },
        "sales chart": {
            "response": "Generated sales trends chart showing 23% increase over last month.",
            "mode": "chart",
            "chart_url": "/static/demo_sales_chart.png"
        }
    },
    "devices": {
        "device count": {
            "response": "Currently monitoring 1,234 IoT devices across 15 locations.",
            "mode": "text"
        },
        "device status": {
            "response": "SELECT status, COUNT(*) as count FROM devices GROUP BY status",
            "mode": "table"
        },
        "temperature data": {
            "response": "Temperature readings from sensors show average of 23.4°C with 2 alerts.",
            "mode": "text"
        }
    },
    "general": {
        "default": {
            "response": "This is a demo version. In production, this would connect to your actual LLM for intelligent responses. The system supports SQL analytics, semantic search, and multi-format responses.",
            "mode": "text"
        }
    }
}

def get_demo_response(message: str, source: str = "financial") -> dict:
    """Get a realistic demo response based on the query."""
    message_lower = message.lower()
    
    # Check for sales-related queries
    if any(keyword in message_lower for keyword in ["sales", "order", "revenue", "product"]):
        if "chart" in message_lower or "graph" in message_lower:
            return DEMO_RESPONSES["sales"]["sales chart"]
        elif "today" in message_lower:
            return DEMO_RESPONSES["sales"]["sales today"]
        elif "top" in message_lower or "best" in message_lower:
            return DEMO_RESPONSES["sales"]["top products"]
        else:
            return DEMO_RESPONSES["sales"]["how many sales"]
    
    # Check for device-related queries
    elif any(keyword in message_lower for keyword in ["device", "sensor", "temperature", "iot"]):
        if "status" in message_lower:
            return DEMO_RESPONSES["devices"]["device status"]
        elif "temperature" in message_lower:
            return DEMO_RESPONSES["devices"]["temperature data"]
        else:
            return DEMO_RESPONSES["devices"]["device count"]
    
    # Default response
    return DEMO_RESPONSES["general"]["default"]
