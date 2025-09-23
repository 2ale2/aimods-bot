from openai import OpenAI
client = OpenAI(api_key="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")

response = client.moderations.create(
    model="omni-moderation-latest",
    input=[{
        "type": "image_url",
        "image_url": {
            "url": "https://x.uuu.cam/pics/spizoo/chloe-surreal/holed-amateur-fistingpinxxx/chloe-surreal-8.jpg"
        }
    }]
)

print(response)