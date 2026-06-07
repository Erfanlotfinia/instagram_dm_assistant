SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "id": "page-123",
            "time": 1717771200000,
            "messaging": [
                {
                    "sender": {"id": "customer-ig-999"},
                    "recipient": {"id": "17841400000000001"},
                    "timestamp": 1717771200000,
                    "message": {
                        "mid": "m_test_message_001",
                        "text": "Hello, I want to order",
                    },
                }
            ],
        }
    ],
}


SAMPLE_SHARED_POST_PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "id": "page-123",
            "messaging": [
                {
                    "sender": {"id": "customer-ig-999"},
                    "recipient": {"id": "17841400000000001"},
                    "timestamp": 1717771300000,
                    "message": {
                        "mid": "m_test_message_002",
                        "attachments": [
                            {
                                "type": "share",
                                "payload": {"url": "https://www.instagram.com/p/ABC123/"},
                            }
                        ],
                    },
                }
            ],
        }
    ],
}
