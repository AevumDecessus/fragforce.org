import random

# Words of 2-3 syllables for stream key generation
WORDS = [
    # Adjectives
    "Amber", "Ancient", "Azure", "Blazing", "Bouncy", "Brazen", "Breezy",
    "Brilliant", "Brimming", "Brindled", "Buoyant", "Buzzing", "Cheerful",
    "Cloudy", "Coastal", "Cobalt", "Crafty", "Crystal", "Dapper", "Dazzling",
    "Dizzy", "Drowsy", "Eager", "Fancy", "Feisty", "Flashy", "Fluffy",
    "Frosty", "Gentle", "Giddy", "Gilded", "Glowing", "Golden", "Grumpy",
    "Glorious", "Hazy", "Hefty", "Hollow", "Icy", "Jolly", "Jumpy",
    "Lofty", "Lucky", "Mellow", "Mighty", "Misty", "Modest", "Murky",
    "Nimble", "Peaceful", "Peppy", "Perky", "Plucky", "Prickly", "Primal",
    "Purple", "Quirky", "Radiant", "Rustic", "Sandy", "Serene", "Silver",
    "Sleepy", "Smoky", "Snappy", "Solar", "Sparkling", "Spunky", "Stormy",
    "Sturdy", "Sunny", "Swanky", "Tender", "Thorny", "Thunder", "Tidy",
    "Timid", "Towering", "Vivid", "Wandering", "Wiry", "Zealous",
    # Nouns - animals
    "Badger", "Beetle", "Bison", "Bluebird", "Bobcat", "Boulder", "Bounty",
    "Buffalo", "Cactus", "Cobra", "Condor", "Coral", "Coyote", "Dingo",
    "Falcon", "Ferret", "Frenzy", "Gecko", "Gibbon", "Goblin", "Gopher",
    "Grizzly", "Harbor", "Hedgehog", "Hippo", "Iguana", "Jackal", "Jaguar",
    "Jellyfish", "Labrador", "Leopard", "Lobster", "Lynx", "Marmot",
    "Meerkat", "Moose", "Narwhal", "Otter", "Panther", "Peacock",
    "Pelican", "Penguin", "Pinto", "Poodle", "Porcupine", "Possum",
    "Puffin", "Python", "Rabbit", "Raven", "Reindeer", "Rooster",
    "Salmon", "Samurai", "Scorpion", "Serpent", "Sparrow", "Spider",
    "Stallion", "Starfish", "Tiger", "Timber", "Toucan", "Tundra",
    "Turtle", "Urchin", "Viper", "Walrus", "Weasel", "Wombat", "Yonder",
    # Nouns - other
    "Anchor", "Bandit", "Beacon", "Blanket", "Blossom", "Blunder",
    "Bonfire", "Bouncer", "Bramble", "Buckle", "Candle", "Cannon",
    "Canyon", "Captain", "Cargo", "Castle", "Cavern", "Cinder",
    "Cipher", "Citrus", "Clamor", "Cobble", "Comet", "Compass",
    "Copper", "Crater", "Crystal", "Dagger", "Ember", "Engine",
    "Fender", "Flannel", "Flicker", "Fossil", "Fracture", "Funnel",
    "Gallop", "Garnet", "Geyser", "Glacier", "Glitter", "Goblet",
    "Gravel", "Grinder", "Hammer", "Harvest", "Helmet", "Hollow",
    "Honey", "Hornet", "Hunger", "Javelin", "Jungle", "Kettle",
    "Lantern", "Lava", "Lumber", "Marble", "Meadow", "Mortar",
    "Mossy", "Muster", "Nectar", "Noodle", "Nugget", "Paddle",
    "Pebble", "Petal", "Pickle", "Pillar", "Pinecone", "Pistol",
    "Plunder", "Pollen", "Powder", "Prism", "Propel", "Puddle",
    "Pumice", "Puzzle", "Quiver", "Ramble", "Rampart", "Rampant",
    "Resin", "Riddle", "Ripple", "Rocket", "Roller", "Rubber",
    "Saddle", "Sandal", "Satchel", "Scepter", "Schooner", "Scimitar",
    "Sector", "Seeker", "Shackle", "Shamble", "Shimmer", "Shovel",
    "Shrapnel", "Shutter", "Signal", "Siren", "Smelter", "Sorrow",
    "Splinter", "Sprocket", "Squander", "Startle", "Stubble", "Sulfur",
    "Summit", "Sunburn", "Surplus", "Tangle", "Tatter", "Tempest",
    "Tender", "Thimble", "Thistle", "Thorn", "Throttle", "Timber",
    "Tinker", "Tipping", "Topple", "Torrent", "Trickle", "Trigger",
    "Tumble", "Tunnel", "Tuner", "Ulcer", "Vapor", "Velvet",
    "Venom", "Vesper", "Victor", "Vigil", "Villain", "Vortex",
    "Wander", "Warden", "Warble", "Wedge", "Whisper", "Wicker",
    "Willow", "Winder", "Winter", "Wonder", "Worthy", "Wrangle",
]


def generate_stream_key():
    """Generate a stream key as 4 capitalized words of 2-3 syllables."""
    return "".join(random.choices(WORDS, k=4))
