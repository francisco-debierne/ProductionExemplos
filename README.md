## Python Instagram Scraper

# Install the requirements

- pip install -r requirements.txt
- docker info:
- docker build -t instagram-scrapper-staging .
- docker run --name instagram-scrapper-staging -d --restart unless-stopped -p 8090:8090 instagram-scrapper-staging


# There are four flask GET endpoints:

- '/user/<username>'
- '/posts/<username>'
- '/post/<shortcode>'
- '/comments/<shortcode>
- '/user_audience/<username>'

# User

As an example, the endpoint user return for the input "heyestrid" is:

```
{
    "info": {
        "biography": "When self-care meets body hair. Real people. 🌈 Real bodies. 🍑 Real smooth razors. 🐬 All hairy & non-hairy humans welcome here. 100% vegan. 🌱",
        "business_category_name": "Personal Goods & General Merchandise Stores",
        "business_email": null,
        "business_phone_number": null,
        "external_url": "http://bit.ly/heyestrid",
        "followers_count": 154629,
        "following_count": 24,
        "full_name": "Estrid",
        "id": "4253931663",
        "is_business_account": true,
        "is_joined_recently": false,
        "is_private": false,
        "posts_count": 972,
        "profile_pic_url": "https://instagram.fmcz9-1.fna.fbcdn.net/v/t51.2885-19/s150x150/118387803_317824012627445_9202083410915652603_n.jpg?_nc_ht=instagram.fmcz9-1.fna.fbcdn.net&_nc_cat=1&_nc_ohc=d_H4t7UbbyAAX-4Qcmr&edm=ABfd0MgBAAAA&ccb=7-4&oh=00_AT_9Wx3wSuT7P5a6N4sxr8V10hpF1z4xBFOhZBG8odU2xA&oe=61CC1486&_nc_sid=7bff83"
    },
    "username": "heyestrid"
}

```

# Posts

This endpoints return the most recent 50 posts of the user.
As an example, the endpoint posts return for the input "heyestrid" is:

```
{
    "posts": [
        {
            "caption": "LAST GIVEAWAY OF THE YEAR 🎄 You and two friends have the chance to win our full merch collection (we might add some extra goodies as well 👀)⁠\n⁠\nThe rules are simple:⁠\n🛁 Follow us @heyestrid⁠\n🛁 Like this post! ⁠\n🛁 Tag two friends that you want to share this giveaway with ⁠\n⁠\nGiveaway ends 31/12. The winner will be randomly selected and contacted through DM. Good luck 💖",
            "comments_number": 1263,
            "dimensions": {
                "height": 1112,
                "width": 1080
            },
            "image_url": "https://instagram.fmcz9-1.fna.fbcdn.net/v/t51.2885-15/e35/p1080x1080/269959682_119281530583399_242105436978329876_n.jpg?_nc_ht=instagram.fmcz9-1.fna.fbcdn.net&_nc_cat=1&_nc_ohc=IS7eDJWSzNAAX8mjnvC&edm=APU89FABAAAA&ccb=7-4&oh=00_AT_9ZuptnLCbpKf7KPRly2IByI12Hy3cic7wWE-QoVE4ww&oe=61CBC841&_nc_sid=86f79a",
            "is_video": false,
            "location": null,
            "shortcode": "CX1ZtBCMvpG",
            "tags": [],
            "likes_number": 0,
            "mentions": [],
            "timestamp": 1640281913,
            "url": "https://instagram.com/p/CX1ZtBCMvpG",
			"video_url":[]
        },
		...
	]
}
```

# Post

This endpoints return the details of a post.
As an example, the endpoint posts return for the input "CXwbBUSJi0a" is:

```
{
    "caption": "Feliz aniversário meu amor @pedrosampaio ... você merece tudo isso que acontece com você e mais um pouco. Que Deus continue morando aí bem dentro do seu coração pra que você seja sempre esse cara extremamente do bem e iluminado. Amo você e sua família demais",
    "carousel": [
        "https://instagram.fmcz9-1.fna.fbcdn.net/v/t51.2885-15/e35/269736904_499040671369781_5982744981310456765_n.jpg?_nc_ht=instagram.fmcz9-1.fna.fbcdn.net&_nc_cat=1&_nc_ohc=fgZBO1ZHzG4AX9ZX_0D&edm=AABBvjUBAAAA&ccb=7-4&oh=00_AT-BMgVeWKWapajx9oD0_1wLxGhSS-g1PHR7OuVZQg695w&oe=61CE0671&_nc_sid=83d603",
        "https://instagram.fmcz9-1.fna.fbcdn.net/v/t51.2885-15/e35/269695666_308075811206163_6970587454847740054_n.jpg?_nc_ht=instagram.fmcz9-1.fna.fbcdn.net&_nc_cat=1&_nc_ohc=M-EWtp4MJl0AX9pVIJU&edm=AABBvjUBAAAA&ccb=7-4&oh=00_AT-n7Uy2_nhhpNlARew5s0dumm6ujzLPK1nn9TTdvi8R-A&oe=61CCEEF7&_nc_sid=83d603"
    ],
    "comments_number": 5075,
    "dimensions": {
        "height": 1349,
        "width": 1080
    },
    "image_url": "https://instagram.fmcz9-1.fna.fbcdn.net/v/t51.2885-15/e35/269695666_308075811206163_6970587454847740054_n.jpg?_nc_ht=instagram.fmcz9-1.fna.fbcdn.net&_nc_cat=1&_nc_ohc=M-EWtp4MJl0AX9pVIJU&edm=AABBvjUBAAAA&ccb=7-4&oh=00_AT-n7Uy2_nhhpNlARew5s0dumm6ujzLPK1nn9TTdvi8R-A&oe=61CCEEF7&_nc_sid=83d603",
    "is_video": false,
    "location": null,
    "mentions": [
        "pedrosampaio"
    ],
    "likes_number": 0,
    "shortcode": "CXwbBUSJi0a",
    "tags": [],
    "timestamp": 1640114831,
    "url": "https://instagram.com/p/CXwbBUSJi0a",
	"video_url":[]
}
```

# Comments 

This endpoints returns between 0 and 250 most recent comments of a posts of the user.
As an example, the endpoint comments return for the input "Bx0NSP5J7Ps" is:

```
{
    "comments": [
        {
            "author_profile_pic": "https://instagram.fmcz9-1.fna.fbcdn.net/v/t51.2885-19/s150x150/125326870_366517927774283_4933967637776897583_n.jpg?_nc_ht=instagram.fmcz9-1.fna.fbcdn.net&_nc_cat=111&_nc_ohc=WE-eL4_dM3IAX_wUaEk&edm=AI-cjbYBAAAA&ccb=7-4&oh=00_AT_jCqtZ09d-t0tFOBBMspVITZb1pgHbMyz78eCRYtN6tg&oe=61CBD983&_nc_sid=ba0005",
            "author_username": "yamithalyssa",
            "text": "Comeback mais esperado de 2019",
            "timestamp": 1558638692
        },
        {
            "author_profile_pic": "https://instagram.fmcz9-1.fna.fbcdn.net/v/t51.2885-19/s150x150/245546901_4535157113217935_2676342575104167530_n.jpg?_nc_ht=instagram.fmcz9-1.fna.fbcdn.net&_nc_cat=111&_nc_ohc=oGIIFpleUxYAX_vHMrR&edm=AI-cjbYBAAAA&ccb=7-4&oh=00_AT_74NJFkih-B61sI2FQBzXNdu16eMRckVFVPgR6psF6kw&oe=61CB819E&_nc_sid=ba0005",
            "author_username": "brsevero22",
            "text": "Voltou \\o/",
            "timestamp": 1558651409
        }
    ]
}
```

# Audience

This endpoint return the information of the audience of an instagram account.
As an example, the endpoint audience return for the input "heyestrid" is:

```
{
    "audience_type": {
        "influencers": 0.0,
        "mass_followers": 3.98,
        "real_people": 90.04,
        "suspicious_accounts": 5.98
    },
    "authenticity": 83.67,
    "reachability": 82.07
}
```