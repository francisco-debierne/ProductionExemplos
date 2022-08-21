import time

from bson import ObjectId
from flask import Flask
from flask_cors import CORS

from ig_utils.IG_Scraper import IG_Scraper


app = Flask(__name__)
CORS(app)

ig = IG_Scraper()


def format_post_data(post: dict, profile_id: ObjectId) -> dict:
    post_object = {}
    post_object['key'] = post['shortcode']
    post_object['username'] = post['author_username']
    post_object['profile'] = ObjectId(profile_id)
    post_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(post['timestamp']))
    post_object['date_time'] = post_time
    post_object['description'] = post['caption']
    post_object['hashtags'] = post['tags']
    post_object['mentions'] = post['mentions']
    post_object['photo_url'] = post['image_url']
    post_object['dimensions'] = post['dimensions']
    post_object['location'] = post['location']
    post_object['total_comments'] = post['comments_number']
    post_object['total_likes'] = post['likes_number']
    
    # Reels Data
    post_object['total_shares'] = post.get('total_shares')
    post_object['total_views'] = post.get('total_views')
    post_object['total_plays'] = post.get('total_plays')
    post_object['video_duration'] = post.get('video_duration')
    
    # carousel data
    post_object['carousel'] = post.get('urls')

    if len(post['video_url']) > 0:
        post_object['video_url'] = post['video_url'][0]
    else:
        post_object['video_url'] = None

    post_object['is_video'] = post['is_video']
    post_object['latest_comments'] = post['latest_comments']
    post_object['permalink'] = post['url']
    post_object['source'] = 'Instagram'
    
    return post_object


@app.route('/', methods=['GET'])
def test_api() -> dict:
    return {'status': 'API Is UP'}


@app.route('/user/<database>/<username>', methods=['GET'])
def get_user_info(database: str, username: str) -> dict:
    ig.connect_mongo(database)
    return ig.scrape(username, 'user')


@app.route('/user_full/<database>/<username>', methods=['GET'])
def get_user_full_info(database: str, username: str) -> dict:
    ig.connect_mongo(database)
    response = {}
    response['user'] = get_user_info(database, username)
    response['posts'] = get_posts_info(database, username)['posts']
    response['follower_list'] = get_user_followers(database, username)['follower_list']
    response['following_list'] = get_user_following(database, username)['following_list']
    return response


@app.route('/posts/<database>/<username>', methods=['GET'])
def get_posts_info(database: str, username: str) -> dict:

    ig.connect_mongo(database)
    col_profiles = ig.mongo.db_client['profiles']
    profile = col_profiles.find_one({"username": username})

    if not profile:
        return {"Message": "This user does not exist in the database"}
    
    posts = ig.scrape(username, 'posts')

    col_posts = ig.mongo.db_client['posts']
    profile_id = profile['_id']

    for post in posts['posts']:
        post_object = format_post_data(post, profile_id)
        
        col_posts.update({'key': post_object['key']}, 
                         post_object,
                         upsert=True)

    print('All posts added successfully')

    return posts


@app.route('/post/<database>/<shortcode>', methods=['GET'])
def get_post_info(database: str, shortcode: str) -> dict:
    post = ig.scrape(shortcode, 'post')

    ig.connect_mongo(database)
    col_profiles = ig.mongo.db_client['profiles']
    
    username = post['author_username']
    profile = col_profiles.find_one({"username": username})

    if not profile:
        return {"Message": "This post's author does not exist in the database"}

    col_posts = ig.mongo.db_client['posts']
    profile_id = profile['_id']

    post_object = format_post_data(post, profile_id)
        
    col_posts.insert_one(post_object)

    return post


@app.route('/comments/<database>/<shortcode>', methods=['GET'])
def get_comments_info(database: str, shortcode: str) -> dict:
    ig.connect_mongo(database)
    comments = ig.scrape(shortcode, 'comments')
    return comments


@app.route('/user_followers/<database>/<username>', methods=['GET'])
def get_user_followers(database: str, username: str) -> dict:
    ig.connect_mongo(database)
    col_profiles = ig.mongo.db_client['profiles']
    profile = col_profiles.find_one({"username": username})
    
    if not profile:
        return {"Message": "This user does not exist in the database"}

    followers = ig.scrape(username, 'followers')

    if 'follower_list' in followers.keys():
        col_profiles.update_one({'username': username},
                                {'$set': {'followers': followers['follower_list']}, 'status': ''})

    return followers


@app.route('/user_following/<database>/<username>', methods=['GET'])
def get_user_following(database: str, username: str) -> dict:
    ig.connect_mongo(database)
    return ig.scrape(username, 'following')


@app.route('/user_audience/<database>/<username>', methods=['GET'])
def get_audience_info(database: str, username: str) -> dict:
    ig.connect_mongo(database)
    col_profiles = ig.mongo.db_client['profiles']
    profile = col_profiles.find_one({"username": username})
    
    if not profile:
        return {"Message": "This user does not exist in the database"}

    col_profiles.update_one({'username': username}, {'$set': {'status': 'Collecting audience.'}})

    try:
        audience = ig.scrape(username, 'audience')

        col_profiles.update_one({'username': username}, {"$set":
                                                         {'audience_type': audience['audience_type'],
                                                          'audience_authenticity': audience['authenticity'],
                                                          'audience_reachability': audience['reachability'],
                                                          'credibility_score': audience['credibility_score'],
                                                          'status': 'Audience collected.'}})
    except:
        col_profiles.update_one({'username': username}, {'$set': {'status': 'Error collecting audience.'}})

    return audience


app.run(host='0.0.0.0', port=8090)

# ig.scrape('', 'comments')

# influencers = "heyestrid"  # ,"curbfood","mathquizily.1","urbanoasisfoods","commutesaver","popswap.app","starpriseofficial","jonnabike","little_snooze","krafthem","thrillism","xroom.app","aline.better","movvioapp","norban.se","hackyourcloset","astridwild_outdoorfashion","printler","migranhjalpen","wearelifelong","mioocycling","sensoremsweden","youareallies","much.skills","memmo_swe","vembla.se","trukatu","noquofoods","medsapotek","tracklib","panion.app","itsreleased","vegobox","buddypetfoods","apohem.se","holmandhimmel","caiacosmetics","voiscooters","freya.se","officialvassla","heapcarsharing","schoolparrot","budkeep","wapdogcare","mendi.io","leafymade","mindlersverige","bringwash","vreel.co","unbiased.ml","virkesborsen","grace.health_","yaytrade","doktor24.se","localfoodnodes","allihoop_","thunderfulgames","nvoiceapp","switchrsolar","anyfin","seraviapp","gigsguide","goodonessverige","preglife","kind.socks","karma_uk","modecoldbrew","botaniumlabs","go_triple","belecointerior","suavoo","we_are_hygglo","bluecallapp","worlds_marathons","sniph","Dashl.se","alteredcompany","savrdotcom","firstvet","doktor.se","poowapplications","flowneuroscience","sjohem.se","enliven.co","diemonde","wayke.se","fliffr","inkbay.tattoo","carledmond","teamuniti","hedvig","insurello_sverige","sana_labs","ridecake","tiptapp_sweden","asket","handiscoverworld","ellypistol","swedenbuyersclub","still.in.fashion","paradiset2.0","matspar.se","bruce.app","nakdfashion","carpetvista","impactpool","impactpool","avionero.news","dibtravel","join_trine","apparkingspot","maklarhemmet","Innoscentia","resolutiongame","byon8_official","snowprintstudios","growwithgaia","braive.one","mapiful","lendifyse","airinum","gluehome","hem","kry.se","qasa.se","tessin_nordic","zynapp","techtroopers_no","xtzsoundinbalance","story_wars","matsmart.se","surfears","dreams.app","auxyco","avawomen","readly","mapillary","refunder.se","nicksicecreams","reve_app","sellpy","idealofsweden","mindoktor","samtrygg","readly","lifesum","youpic","quindo","soundtrap","orbitalsystems","simris","happyplugs","auctionet","fishbrainapp","learningtosleep","fundedbyme","minuthq","fyndiq","ignitiaweather","truecaller","zoundindustries","pixlr","fatsharkgames","https:sello.ioen","mathem","apotea.se","royaldesign","kidsbrandstore","_usedby_","tatoveringfordeg.no","videolegevakt","somlos_official","wam_app","advokatguiden.no","sweettrollgames","aniport.no","spahuset","coinpanda_io","waydmoments","vagpwrbybecker","aswearenow_","minuendosound","equality_check","grogrofood","lendonomy","soothing.relaxation","empowerplastic","aukeco","horde.app","zabaitraining","newmovements","diwala_","unloc.app","chooosetoday","enjoy_norge","eir_of_norway","vipicash","lifekeys.international","wattero_","moodielive","exero_technologies","voed.co","bakengo.app","mangfold_forlag","lastcall_app","fjongofficial","tibber_norge","bookisofficial","otovosolar","tikktalk","carepacks.co","grontskift","wiralcam","gopayr_","eyr_norge","styletime_no","boldbooks_as","beyourbest_pro","uniteliving","dyrket.no","tradematesports","learnlink.no","joymo_tv","thepodbike","epleslang_","moviemask","nanook.travel","samme_vei","villoid.no","tise","halodirobotics","nabobil_by_getaround","getspiff","_noisolation","bagidofficial","movingmamas","fineswap","thenortherncompany","younghappyminds","weclean.no","dyrekassen.no","resani_sanitizing","playmagnus","kolonial.no","remarkable","staaker","getkahoot","meglersidenno","stayouttt","nofence","brightproducts","blushno","KickBack.no","glitnehalibut","SWIMSofficial","finn_no","northernplayground","waior_","saleablcom","exhibiaauction","sirumobile","bonusway.fi","singakaraoke","ouraring","valpashotels","cozify_smarthome","virtaltd","meetingpackage","funzimobi","woltapp","Kideapp","mightifierapp","zadaa_de","pockethunt","rekkifi","moominls","familywithkids","freska.fi","goodiogoods","quieton","kiekuaudio","teatiamo","swappiecom","thedoerz","meru_health","inventshift","blokhomes","kidescience","wowandersapp","graphogame","omago.fi","surrogate.tv","bobwco","nomi.style","sorttersuomi","kotikyla_com","alvarpet","sustainonline","sonant.app","becomeoyama","letstepout","perille_fi","warriorcoffeeco","helloruby.world","storyofroo","fiksuruoka.fi","coolerfuture","yousician","neverthink.tv","beddit","yogaiaofficial","epicfoodsco","tespack","venuufi","klinik.fi","tori_fi","transfluent_inc","lainaaja.fi","swap_com","hintsaperformance","demotuwatches","kasperibags","rensoriginal","loviacollection","soupstercatering","caramelhelsinki","helsieni","viikinkiravintola_harald","fruitkit","sayduckar","cazoo","pollen_uk","selina","snaptraveltech","emoctoofficial","lakahq","feralhorses","boufdotcom","stasherofficial","theshopperdotcom","press_healthfoods","arena_flowers","drfelixpharmacy","vitlhealth","mykidsitter_","cudoniuk","velorutionlondon","mountainwarehouse","lovespaceuk","komodofashion","rapha","lyst","heromag","fetchlovespets","lilasjewels","pastaevangelists","modernmilkman_","seraphinematernity","_fashionmusa_","float.delivery","competeimpossible","imaginecurve","monzo","etoro_official","gocardless","babylonhealth","seedrs","farfetch","worldremit","patchplants","echo_pharmacy","secretescapes","lendinvest","citymapper","blockchainofficial","depop","sofarsounds","thenutmegteam","elvie","deliveroo","culturetrip","festicket","revolutapp","faceitcom","goustocooking","transfergo","habitoloveshomes","carwow","yoyowalletapp","madedotcom","get_chip","bulb","everledger","clear.bank","bitstampexchange","moneyboxteam","starlingbank","totallymoney","koyoloans","proportunity","mishipayapp","hownowhq","wagestream","discover.film","bloomandwild","allplants","joinmultiverse","smarketshq","milkstercreamery","pactcoffee","holvi","appearherehq","gosimpletax","24symbols","riseart","peaklabs","carthrottle","onefinestay","jobandtalent","treatwell_uk","busuu","zoopla","marvelapp","threadformen","cafedirect","tastebudsfm","last_fm","gettyimages","medicanimal_","airesquad","justparkhq","moshisleep","badoo","audionetwork","bidvine","mixlr","artfinder_com","Zopamoney","mixcloud","justeatuk","tribesports","citysocializer","moo","pitchupcom","learningwithexperts","teamkano","hubblehq","cryptopayofficial","snapfashion","grabble","boilerroomtv","reedsy_hq","gocarshare","healthunlocked","goodnightlamp","boomf","wonderbly","spoke_london","urbanapp","primotoys","spectrocoin","toothpick.app","encoremusicians","nightzookeeper","wolfandbadger","etfmatic","Pinktrotters","fundingoptionsuk","monese","bleepbleeps","hopstertv","boardaboat","bookofeveryone","pearsonstudents","we.are.roli","objeststyle","dicefm","teststudiet.dk","ngener.io","fluentoacademy","kaspar.ai","custimy.io","leadfamly","sharing_market","makeitworthmore","bynielsendenmark","stocko.pro","travelkollekt","workee_app","reepaycom","fooducer_com","oveo_io","gamerzclass","undy.dk","videojaguar","podimo_global","careermentor.dk","fooducer_com","nordic_digital_lab","decorRaid","jumpstoryofficial","eatgrim","wedio_community","heydesk","morningscore","findmaaltidskasser","goodmonday.io","map_view","nordic_digital_lab","salvatio_push","we.care.health","digura_dk","rizingplaylists","eatmoredk","joinlifex","traefolk","lifeatkeepit","nordgreenofficial","andsimpleco","danishstartupgroup","ooolio_fashion","finematter","trainaway","zolesdk","cobiroinc","manillodk","legalherohq","playdeadgames","mate.bike","investwiththemany","hooves_app","luggagehero","packitupteam","toogoodtogo.uk","skidos_games","reepaycom","mearto_com","dixa.io","anyware.solutions","lunar","kubo_robotics","djhusetdk","simplefeastdenmark","celinakollektion","happyhelper.dk","imarit.fashion","getlinkfire","katoni.dk","bluecitydk","boatflex","bownty_dk","sonofatailor","donkey_republic","heartbeatsdk","finansdk","biva.dk","musikundervisning.dk","nohrlund","momio_official","24syv_app","artboost","sitpackofficial","emsbodypower","officialcoderstrustglobal","tattoodo","ernit_piggybank","roccamore_shoes","goodieboxdenmark","writereaderapp","bemyeyesapp","haisler_resell","labstergram","bownty_dk","paiblockapp","onlinesupplies_kontorartikler","digizuite","fiverr","getyourguide","chronext","gorillasapp","getgrover","navabifashion","the_caroobians","watchmaster_com","petsdeli","bestsecret","yfood","gittibeauty","everdrop","asgoodasnewde","roombles.app","wundercurves.de","combyneapp","lassig_gmbh","thestorymarket.co","textcortex","picter_com","gittibeauty","dglegacy","autoretouch","implify_de","mijo_brand","trypult","purishcom","slicebusiness","fleksaofficial","juno.app","kolokoapp","writeaguide","circles_fr","thecalmbase","brajuu.tech","getquin","chatterbug.app","editwithtype","nunkreativa","expozed1.de","facen_original","doctoryou.de","superchatde","climo.io","tokenstreet","truemorrow.de","triplegend","editwithtype","v__and__you","spoondrink","tomorrows.education","along_space","up42official","kenjo_hr","sockstock.onlineshop","unownfashion","happyhotel.io","aivy.app","staiy_official","getblock.io","aidaform","grailify","speechtext.ai","circlybeauty","pureganic.de","evope_europe","keeet.io","arvaloo.official","getciara","beducatedcom","saenguin","undabottle","kulero.de","inhubber","cotasker","vytal_global","twostay.work","better.by.less","tierscooter","mundusskincare","instagridpower","chemondis.career","twostay.work","cgift_","mundusskincare","openhandwerk","productswithlove.de","getmyinvoices_english","sushibikes","PitchHQ","share.your.space","airup","levericegram","recooty","straffr.official","myurmo","qvsta"]

# ig.scrape(influencers)
