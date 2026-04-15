import re
import logging
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)


class ProfileMissingError(Exception):
    """Raised when a required user profile is absent or critically incomplete."""
    pass


class ProfileContext:
    """
    Single owner of all profile-related logic for Jema.
    Instantiate once per request/message with the user profile dict.
    Pass the instance into JemaEngine and LLMService instead of the raw dict.
    """

    def __init__(self, user_profile: Optional[dict]):
        """
        Initialize ProfileContext with user profile validation.
        
        Step 1 — Validate profile. If user_profile is None or not a dict, raise ProfileMissingError.
        Step 2 — Store the raw profile.
        Step 3 — Normalise and extract all fields at init time.
        Step 4 — Build the forbidden ingredient set once.
        Step 5 — Log a confirmation.
        """
        # Step 1: Validate profile
        if user_profile is None or not isinstance(user_profile, dict):
            raise ProfileMissingError(
                "User profile is required. Please complete your profile setup."
            )

        # Step 2: Store raw profile
        self.profile = user_profile

        # Step 3: Normalise and extract all fields
        self.religion = str(user_profile.get("religion") or "").lower().strip()
        self.diet = str(user_profile.get("diet") or "").lower().strip()
        self.goal = str(user_profile.get("goal") or "").lower().strip()
        self.cooking_level = str(
            user_profile.get("cooking_level") or "novice"
        ).lower().strip()
        self.income = str(user_profile.get("income") or "").lower().strip()
        self.calorie_target = user_profile.get("calorie_target") or 2000
        self.dislikes = self._normalise_list(user_profile.get("dislikes"))
        self.allergies = self._normalise_list(user_profile.get("allergies"))
        self.medical_conditions = self._normalise_list(
            user_profile.get("medical_conditions")
        )

        # Step 4: Build the forbidden ingredient set once
        self.forbidden = self._build_forbidden_set()

        # Step 5: Log a confirmation
        logger.debug(
            f"[ProfileContext] Loaded — diet={self.diet}, religion={self.religion}, "
            f"allergies={self.allergies}, medical={self.medical_conditions}, "
            f"forbidden_count={len(self.forbidden)}"
        )

    def _normalise_list(self, value) -> list:
        """
        Normalise a value (None, string, or list) into a list of lowercased stripped strings.
        
        Examples:
            None -> []
            "nuts, fish" -> ["nuts", "fish"]
            ["Nuts", " Fish "] -> ["nuts", "fish"]
            "diabetes" -> ["diabetes"]
        """
        if value is None:
            return []
        
        if isinstance(value, str):
            # Split by comma and normalize each item
            items = value.split(",")
            return [item.lower().strip() for item in items if item.lower().strip()]
        
        if isinstance(value, list):
            # Normalize each item in the list
            return [
                str(item).lower().strip() for item in value
                if str(item).lower().strip()
            ]
        
        return []

    def _build_forbidden_set(self) -> set:
        """
        Build and return a complete set of forbidden ingredient tokens derived from the profile.

        Implements dietary, religious, allergy, dislikes, and medical rules.
        Sources: CDC, Diabetes UK, Mayo Clinic, Harvard Health, American Heart Association,
                 National Kidney Foundation, Diet Doctor, WebMD.
        """
        forbidden = set()

        # ─────────────────────────────────────────────
        # DIETARY RULES
        # ─────────────────────────────────────────────

        if self.diet in ("vegan", "hindu_vegetarian"):
            forbidden.update([
                # All meat
                "chicken", "beef", "lamb", "mutton", "goat", "pork", "turkey", "duck",
                "rabbit", "venison", "bison", "veal", "offal", "liver", "kidney",
                "tripe", "oxtail", "intestine", "bone marrow",
                # All seafood
                "fish", "salmon", "tuna", "cod", "tilapia", "catfish", "mackerel",
                "sardine", "sardines", "anchovy", "anchovies", "herring", "trout",
                "haddock", "snapper", "grouper", "perch", "bream", "carp",
                "prawn", "shrimp", "crab", "lobster", "oyster", "clam", "mussel",
                "scallop", "squid", "octopus", "crayfish", "cuttlefish",
                # Processed meat
                "meat", "bacon", "ham", "sausage", "salami", "pepperoni", "chorizo",
                "lard", "suet", "tallow", "dripping", "gelatin", "gelatine",
                "rennet", "isinglass",
                # All dairy
                "milk", "whole milk", "skimmed milk", "evaporated milk",
                "condensed milk", "powdered milk", "buttermilk", "cream",
                "heavy cream", "double cream", "sour cream", "creme fraiche",
                "cheese", "cheddar", "mozzarella", "parmesan", "feta",
                "ricotta", "gouda", "brie", "camembert", "halloumi",
                "butter", "ghee", "clarified butter",
                "yogurt", "yoghurt", "greek yogurt", "kefir",
                "whey", "casein", "lactose",
                # Eggs and egg products
                "egg", "eggs", "egg yolk", "egg white", "mayonnaise",
                "meringue", "albumen",
                # Other animal products
                "honey", "beeswax", "royal jelly",
                # Animal-derived stocks and fats
                "chicken stock", "beef stock", "chicken broth", "beef broth",
                "bone broth", "fish stock", "fish sauce", "oyster sauce",
                "worcestershire sauce", "meat stock", "stock cube",
            ])

        if self.diet == "vegetarian":
            forbidden.update([
                # All meat
                "chicken", "beef", "lamb", "mutton", "goat", "pork", "turkey", "duck",
                "rabbit", "venison", "bison", "veal", "offal", "liver", "kidney",
                "tripe", "oxtail", "intestine", "bone marrow",
                # All seafood
                "fish", "salmon", "tuna", "cod", "tilapia", "catfish", "mackerel",
                "sardine", "sardines", "anchovy", "anchovies", "herring", "trout",
                "haddock", "snapper", "grouper", "prawn", "shrimp", "crab",
                "lobster", "oyster", "clam", "mussel", "scallop", "squid", "octopus",
                "crayfish",
                # Processed meat
                "meat", "bacon", "ham", "sausage", "salami", "pepperoni", "chorizo",
                "lard", "suet", "tallow", "dripping", "gelatin", "gelatine",
                # Animal-derived stocks and sauces
                "chicken stock", "beef stock", "chicken broth", "beef broth",
                "bone broth", "fish stock", "fish sauce", "oyster sauce",
                "worcestershire sauce", "meat stock",
            ])

        if self.diet == "pescatarian":
            forbidden.update([
                # All land meat only — fish/seafood is allowed
                "chicken", "beef", "lamb", "mutton", "goat", "pork", "turkey", "duck",
                "rabbit", "venison", "bison", "veal", "offal", "liver", "kidney",
                "tripe", "oxtail", "intestine", "bone marrow",
                "meat", "bacon", "ham", "sausage", "salami", "pepperoni", "chorizo",
                "lard", "suet", "tallow",
                # Land-meat stocks
                "chicken stock", "beef stock", "chicken broth", "beef broth",
                "bone broth", "meat stock",
            ])

        if self.diet == "keto":
            forbidden.update([
                # All grains and grain-derived products
                "rice", "white rice", "brown rice", "basmati rice", "jasmine rice",
                "wild rice", "rice flour", "rice cake",
                "bread", "white bread", "brown bread", "wheat bread", "flatbread",
                "pita", "naan", "injera", "chapati", "roti", "tortilla", "wrap",
                "pasta", "spaghetti", "noodles", "macaroni", "vermicelli",
                "flour", "white flour", "wheat flour", "self-raising flour",
                "cornmeal", "cornflour", "corn starch", "corn syrup",
                "oats", "oatmeal", "porridge", "muesli", "granola",
                "cereal", "breakfast cereal",
                "barley", "rye", "spelt", "farro", "millet", "teff",
                "quinoa", "amaranth", "buckwheat", "sorghum",
                "semolina", "couscous", "bulgur", "durum",
                "crackers", "biscuit", "cookie",
                # Starchy vegetables and tubers
                "potato", "potatoes", "sweet potato", "yam", "yams",
                "cassava", "fufu", "eba", "amala", "pounded yam",
                "plantain", "unripe plantain", "ripe plantain",
                "taro", "cocoyam", "arrowroot", "parsnip",
                "beet", "beetroot", "corn", "maize",
                # Legumes (high carb for keto)
                "beans", "black beans", "kidney beans", "pinto beans",
                "chickpeas", "garbanzo", "lentils", "dal", "dhal",
                "black-eyed peas", "cowpeas", "split peas",
                "edamame", "broad beans", "fava beans",
                # Sugars and sweeteners (all forms)
                "sugar", "white sugar", "brown sugar", "cane sugar",
                "icing sugar", "powdered sugar", "raw sugar",
                "honey", "maple syrup", "agave", "agave nectar",
                "molasses", "treacle", "golden syrup", "corn syrup",
                "high fructose corn syrup", "fructose", "glucose",
                "dextrose", "maltose", "sucrose", "lactose",
                "fruit juice", "juice", "fruit juice concentrate",
                "jam", "jelly", "preserve",
                # High-sugar fruits
                "banana", "mango", "grape", "grapes", "pineapple",
                "watermelon", "papaya", "lychee", "dates", "dried fruit",
                "raisins", "sultanas",
                # Processed and packaged carbs
                "maltodextrin", "modified starch", "tapioca",
            ])

        # ─────────────────────────────────────────────
        # RELIGIOUS RULES
        # ─────────────────────────────────────────────

        if "muslim" in self.religion or "halal" in self.religion:
            forbidden.update([
                # Pork and all pork derivatives
                "pork", "pig", "bacon", "ham", "gammon", "pancetta",
                "prosciutto", "salami", "pepperoni", "chorizo",
                "sausage",  # unless confirmed halal
                "lard", "pork lard", "pork fat", "pork rind", "crackling",
                "gelatin", "gelatine",  # often pork-derived
                # All alcohol and alcohol-derived products
                "alcohol", "wine", "red wine", "white wine", "rose wine",
                "beer", "lager", "stout", "ale", "cider",
                "spirits", "rum", "vodka", "whiskey", "whisky",
                "brandy", "gin", "tequila", "sake", "mead",
                "champagne", "prosecco",
                "cooking wine", "wine vinegar", "balsamic vinegar",
                "vanilla extract",  # alcohol-based; use vanilla powder instead
                "marsala", "sherry", "port",
                "liqueur", "schnapps",
            ])

        if "hindu" in self.religion:
            forbidden.update([
                "beef", "veal", "bison",
                # Many Hindus also avoid all meat — handled by hindu_vegetarian diet
            ])

        if "jewish" in self.religion or "kosher" in self.religion:
            forbidden.update([
                # Non-kosher meats
                "pork", "bacon", "ham", "lard", "gammon",
                # Non-kosher seafood (no fins and scales)
                "shellfish", "prawn", "shrimp", "crab", "lobster",
                "oyster", "clam", "mussel", "scallop", "crayfish",
                "squid", "octopus",
                # Mixing meat and dairy (flagged as a warning in prompts)
                # (Cannot enforce mixing at ingredient level — handled in prompt)
            ])

        # ─────────────────────────────────────────────
        # ALLERGY RULES
        # ─────────────────────────────────────────────

        for allergy in self.allergies:
            al = allergy.lower().strip()

            if "nut" in al or al in ("nuts", "groundnut", "groundnuts", "peanut", "peanuts", "tree nut"):
                forbidden.update([
                    # Tree nuts
                    "almond", "almonds", "almond flour", "almond milk", "almond butter",
                    "cashew", "cashews", "cashew milk", "cashew butter",
                    "walnut", "walnuts",
                    "pistachio", "pistachios",
                    "hazelnut", "hazelnuts", "hazelnut butter",
                    "pecan", "pecans",
                    "macadamia", "macadamia nut",
                    "pine nut", "pine nuts",
                    "chestnut", "chestnuts",
                    "brazil nut", "brazil nuts",
                    # Peanuts (legume but common allergy)
                    "peanut", "peanuts", "groundnut", "groundnuts",
                    "peanut butter", "groundnut oil", "peanut oil",
                    # General
                    "nut", "nuts", "nut oil", "nut flour", "nut milk",
                    "mixed nuts", "praline", "marzipan", "nougat",
                ])

            if "dairy" in al or al in ("lactose", "milk", "lactose intolerance"):
                forbidden.update([
                    "milk", "whole milk", "skimmed milk", "semi-skimmed milk",
                    "evaporated milk", "condensed milk", "powdered milk",
                    "buttermilk", "cream", "heavy cream", "double cream",
                    "single cream", "sour cream", "creme fraiche",
                    "cheese", "cheddar", "mozzarella", "parmesan", "feta",
                    "ricotta", "gouda", "brie", "camembert", "halloumi",
                    "cream cheese", "cottage cheese",
                    "butter", "ghee", "clarified butter",
                    "yogurt", "yoghurt", "greek yogurt", "kefir",
                    "whey", "whey protein", "casein", "lactose",
                    "ice cream", "milkshake", "custard",
                ])

            if "gluten" in al or "wheat" in al or "celiac" in al or "coeliac" in al:
                forbidden.update([
                    "wheat", "wheat flour", "white flour", "wholemeal flour",
                    "bread", "breadcrumbs", "croutons",
                    "pasta", "noodles", "couscous",
                    "barley", "rye", "spelt", "kamut", "einkorn", "emmer",
                    "semolina", "bulgur", "farro", "triticale",
                    "oats", "oatmeal",  # often cross-contaminated
                    "malt", "malt vinegar", "barley malt",
                    "soy sauce",  # most contain wheat
                    "seitan", "wheat gluten",
                    "batter", "flour coating",
                ])

            if "shellfish" in al or "seafood" in al:
                forbidden.update([
                    "shrimp", "prawn", "crab", "lobster", "oyster",
                    "clam", "scallop", "mussel", "squid", "octopus",
                    "crayfish", "barnacle", "sea urchin",
                    "cuttlefish", "abalone",
                ])

            if "fish" in al:
                forbidden.update([
                    "fish", "salmon", "tuna", "cod", "tilapia", "catfish",
                    "mackerel", "sardine", "sardines", "anchovy", "anchovies",
                    "herring", "trout", "haddock", "snapper", "grouper",
                    "bream", "carp", "perch", "swordfish", "halibut",
                    "fish sauce", "fish stock", "fish oil",
                ])

            if "egg" in al or al == "eggs":
                forbidden.update([
                    "egg", "eggs", "egg yolk", "egg white",
                    "mayonnaise", "aioli", "meringue", "albumen",
                    "egg noodles", "egg pasta", "egg wash",
                ])

            if "soy" in al or "soya" in al:
                forbidden.update([
                    "soy", "soya", "tofu", "tempeh", "miso",
                    "edamame", "soy sauce", "tamari", "soy milk",
                    "soy protein", "textured vegetable protein", "tvp",
                    "soybean oil", "soy lecithin",
                ])

        # ─────────────────────────────────────────────
        # DISLIKES
        # ─────────────────────────────────────────────

        forbidden.update(self.dislikes)

        # ─────────────────────────────────────────────
        # MEDICAL RULES
        # ─────────────────────────────────────────────

        for condition in self.medical_conditions:
            cond = condition.lower().strip()

            # ── DIABETES ──────────────────────────────
            if "diabetes" in cond or "diabetic" in cond:
                forbidden.update([
                    # Direct sugars — all names and aliases
                    "sugar", "white sugar", "brown sugar", "cane sugar",
                    "raw sugar", "icing sugar", "powdered sugar",
                    "castor sugar", "turbinado sugar", "demerara sugar",
                    "palm sugar", "date sugar", "coconut sugar",
                    # Syrups
                    "corn syrup", "high fructose corn syrup", "hfcs",
                    "glucose syrup", "maple syrup", "golden syrup",
                    "agave", "agave nectar", "agave syrup",
                    "molasses", "treacle", "rice syrup",
                    "honey",  # spikes blood sugar despite being natural
                    # Monosaccharides and disaccharides
                    "glucose", "fructose", "dextrose", "sucrose",
                    "maltose", "lactose",  # latter tolerable in small amounts but flagged
                    # Processed starches with high glycaemic index
                    "maltodextrin",  # GI of 85–105, higher than table sugar
                    "modified starch", "hydrolysed starch",
                    "tapioca", "tapioca starch",
                    # Refined grains (rapidly convert to glucose)
                    "white rice", "white bread", "white flour",
                    "white pasta", "refined flour", "plain flour",
                    # Sugary drinks and concentrates
                    "soda", "soft drink", "cola", "lemonade",
                    "fruit juice", "juice", "fruit juice concentrate",
                    "sports drink", "energy drink", "sweetened drink",
                    "sweet tea", "sweetened tea", "flavoured milk",
                    # Confectionery and baked sweets
                    "candy", "sweets", "chocolate bar", "toffee", "caramel",
                    "fudge", "nougat", "marshmallow",
                    "cake", "cupcake", "muffin", "doughnut", "donut",
                    "biscuit", "cookie", "pastry", "croissant",
                    "ice cream", "gelato", "sorbet",
                    # Sweetened condiments (often invisible sugar sources)
                    "ketchup", "tomato ketchup", "bbq sauce", "barbecue sauce",
                    "sweet chilli sauce", "hoisin sauce", "teriyaki sauce",
                    "sweet and sour sauce", "jam", "jelly", "preserve",
                    "marmalade", "chocolate spread", "nutella",
                    # High-GI starchy African staples
                    "white fufu", "eba", "garri",  # processed cassava — very high GI
                ])

            # ── HYPERTENSION ──────────────────────────
            if "hypertension" in cond or "hypertensive" in cond or "high blood pressure" in cond:
                forbidden.update([
                    # Salt and all sodium-heavy seasonings
                    "salt", "table salt", "sea salt", "rock salt", "pink salt",
                    "himalayan salt", "kosher salt", "celery salt", "garlic salt",
                    # Stock cubes and bouillon (extremely high sodium)
                    "stock cube", "bouillon", "bouillon cube",
                    "maggi", "knorr", "royco", "jumbo cube", "seasoning cube",
                    "chicken stock cube", "beef stock cube",
                    "chicken stock", "beef stock",  # unless unsalted/low sodium
                    # Salty condiments and sauces
                    "soy sauce", "tamari", "fish sauce", "oyster sauce",
                    "worcestershire sauce", "miso", "miso paste",
                    "teriyaki sauce", "hoisin sauce",
                    "ketchup",  # also high sugar
                    "salted butter",
                    # Processed and cured meats
                    "processed meat", "salami", "pepperoni", "chorizo",
                    "sausage", "hot dog", "frankfurter", "bologna",
                    "bacon", "ham", "luncheon meat", "spam",
                    "smoked meat", "cured meat", "deli meat",
                    "corned beef", "biltong",  # high sodium
                    # Pickled and preserved foods
                    "pickle", "pickled vegetables", "pickled fish",
                    "canned fish", "canned meat", "canned soup",
                    # High-sodium African pantry staples
                    "dawadawa",  # fermented locust beans — high sodium
                    "ogiri", "iru",  # fermented items — high sodium
                    # Added sugar also worsens hypertension
                    "sugar", "corn syrup", "high fructose corn syrup",
                ])

            # ── ANTI-INFLAMMATORY ─────────────────────
            if "anti-inflammatory" in cond or "inflammation" in cond or "inflammatory" in cond:
                forbidden.update([
                    # Refined sugars (all forms)
                    "sugar", "white sugar", "brown sugar", "icing sugar",
                    "corn syrup", "high fructose corn syrup",
                    "glucose syrup", "fructose", "dextrose", "maltose",
                    # Refined grains and white starches
                    "white flour", "refined flour", "white bread",
                    "white rice", "white pasta",
                    "refined cereal", "sugary cereal",
                    # Trans fats and pro-inflammatory oils
                    "margarine", "vegetable shortening",
                    "partially hydrogenated oil", "hydrogenated oil",
                    "corn oil", "soybean oil", "cottonseed oil",
                    "safflower oil",  # high omega-6
                    # Processed meats
                    "processed meat", "bacon", "hot dog", "sausage",
                    "salami", "pepperoni", "deli meat", "luncheon meat",
                    # Full-fat and processed dairy
                    "butter", "whole milk", "full-fat cheese",
                    "processed cheese", "nacho cheese",
                    # Fried foods (flagged generically)
                    "deep fried", "deep-fried",
                    # Artificial sweeteners (some trigger inflammation)
                    "aspartame", "sucralose", "saccharin",
                    # Excess omega-6 oils already listed above
                ])

            # ── LOW-FODMAP ────────────────────────────
            if "fodmap" in cond or "low-fodmap" in cond or "ibs" in cond:
                forbidden.update([
                    # High-FODMAP fruits
                    "apple", "pear", "mango", "cherry", "watermelon",
                    "peach", "plum", "nectarine", "apricot",
                    "dried fruit", "dates", "figs",
                    # High-FODMAP vegetables
                    "onion", "garlic", "leek", "shallot", "spring onion",
                    "cauliflower", "mushroom", "mushrooms",
                    "asparagus", "artichoke", "beetroot",
                    # Legumes
                    "lentils", "chickpeas", "kidney beans", "black beans",
                    "baked beans",
                    # Grains with fructans
                    "wheat", "rye", "barley",
                    # Dairy with lactose
                    "milk", "ice cream", "custard", "condensed milk",
                    "soft cheese", "cream cheese", "ricotta",
                    # Sweeteners
                    "honey", "agave", "high fructose corn syrup",
                    "sorbitol", "mannitol", "xylitol", "maltitol",
                ])

        return forbidden

    def filter_csv(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter the DataFrame to rows safe for this profile.
        Returns a non-empty DataFrame always — degrades gracefully if filtering is too strict.
        """
        logger.debug(f"[ProfileContext] filter_csv() called — input rows: {len(df)}, forbidden_count={len(self.forbidden)}")
        if len(df) == 0:
            return df

        # Step 1: Full filter (diet + religion + allergy + dislikes)
        def row_is_safe(row):
            core_ingredients = str(row.get("core_ingredients", "")).lower()
            for token in self.forbidden:
                if re.search(r'\b' + re.escape(token.lower()) + r'\b', core_ingredients):
                    return False
            return True

        full_filtered = df[df.apply(row_is_safe, axis=1)]
        logger.debug(f"[ProfileContext] filter_csv() full filter — output rows: {len(full_filtered)}")

        # Step 2: If full filter yields results, return it
        if len(full_filtered) >= 1:
            return full_filtered

        # Step 3: Partial filter (drop dislikes, keep hard constraints only)
        hard_forbidden = self.forbidden - set(self.dislikes)

        def row_is_safe_hard(row):
            core_ingredients = str(row.get("core_ingredients", "")).lower()
            for token in hard_forbidden:
                if re.search(r'\b' + re.escape(token.lower()) + r'\b', core_ingredients):
                    return False
            return True

        partial_filtered = df[df.apply(row_is_safe_hard, axis=1)]

        # Step 4: If partial filter yields results, return it
        if len(partial_filtered) >= 1:
            logger.warning(f"[ProfileContext] filter_csv() full filter left 0 rows — falling back to hard constraints only")
            return partial_filtered

        # Step 5: Last resort — return original df unchanged
        logger.warning(f"[ProfileContext] filter_csv() all filters left 0 rows — returning unfiltered df")
        return df

    def build_personalisation_block(self) -> str:
        """
        Build and return the system prompt personalisation block for the LLM.
        Always returns a non-empty string. Never returns "" or None.
        """
        sections = []

        # Section 1: ABSOLUTE DIETARY PROHIBITIONS
        forbidden_list = ", ".join(sorted(self.forbidden))
        logger.debug(f"[ProfileContext] build_personalisation_block() called — building for diet={self.diet}, religion={self.religion}")
        section1 = (
            "ABSOLUTE DIETARY PROHIBITIONS — Never include any of the following in any suggestion, "
            "recipe, ingredient list, or tip, regardless of health benefit claims:\n"
            f"{forbidden_list}"
        )
        sections.append(section1)

        # Section 2: RELIGIOUS REQUIREMENTS (if religion is set)
        if self.religion:
            if "muslim" in self.religion or "halal" in self.religion:
                sections.append(
                    "HALAL REQUIREMENT — All food must be halal. Never mention pork, alcohol, lard, "
                    "gelatin (unless certified halal), or any derivative, even as a substitution or comparison."
                )
            if "hindu" in self.religion:
                sections.append(
                    "HINDU DIETARY REQUIREMENT — Never include beef or veal. Vegetarian rules apply if diet is set to vegetarian."
                )
            if "jewish" in self.religion or "kosher" in self.religion:
                sections.append(
                    "KOSHER REQUIREMENT — Never mix meat and dairy in the same dish. Never include pork or shellfish."
                )

        # Section 3: FITNESS GOAL (if goal is set)
        if self.goal:
            if self.goal == "lose weight":
                sections.append(
                    f"WEIGHT LOSS GOAL — Prioritise low-calorie, high-fibre, low-fat preparations. "
                    f"Daily target: {self.calorie_target} kcal. Mention portion sizes."
                )
            elif self.goal == "muscle_gain":
                sections.append(
                    f"MUSCLE GAIN GOAL — Prioritise high-protein meals. "
                    f"Daily target: {self.calorie_target} kcal. Mention protein content."
                )
            elif self.goal == "eat healthier":
                sections.append(
                    f"EAT HEALTHIER GOAL — Prioritise whole foods, minimal processing. "
                    f"Daily target: {self.calorie_target} kcal."
                )
            elif self.goal == "maintain":
                sections.append(
                    f"MAINTENANCE GOAL — Balanced macros. Daily target: {self.calorie_target} kcal."
                )

        # Section 4: MEDICAL CONDITIONS (if any)
        for condition in self.medical_conditions:
            if "diabetes" in condition or "diabetic" in condition:
                sections.append(
                    "DIABETES MANAGEMENT — Avoid high-GI foods (white rice, white bread, sugar, syrup). "
                    "The Tips section of every recipe MUST include a blood sugar management note."
                )
            elif "hypertension" in condition or "hypertensive" in condition:
                sections.append(
                    "HYPERTENSION MANAGEMENT — No stock cubes, Maggi, Knorr, or high-sodium ingredients. "
                    "The Tips section MUST include a low-sodium note."
                )
            else:
                sections.append(
                    f"MEDICAL NOTE — User has {condition}. Tailor tips accordingly."
                )

        # Section 5: COOKING LEVEL
        if self.cooking_level in ("novice", "basic"):
            sections.append(
                "COOKING LEVEL: NOVICE — Use plain everyday language. No technical culinary terms. "
                "Keep steps short and numbered. Explain every technique."
            )
        elif self.cooking_level == "intermediate":
            sections.append(
                "COOKING LEVEL: INTERMEDIATE — Standard culinary language acceptable. Some technique assumed."
            )
        elif self.cooking_level == "advanced":
            sections.append(
                "COOKING LEVEL: ADVANCED — Professional terminology acceptable. Assume full kitchen competence."
            )

        # Section 6: INCOME / BUDGET (if income is set)
        if self.income == "low":
            sections.append(
                "BUDGET: LOW INCOME — Suggest affordable, widely available ingredients. No premium or specialty items."
            )

        # Section 7: UNIVERSAL STOCK RULE (always append)
        sections.append(
            "STOCK CUBE RULE — Never use stock cubes, Maggi, Knorr, or bouillon in any recipe. "
            "Always substitute with homemade stock or water with spices."
        )

        # Join all sections with newlines
        block = "\n\n".join(sections)

        # Fallback (should never be reached if forbidden is always non-empty)
        if not block or len(block.strip()) == 0:
            block = (
                "SAFETY DEFAULT — No user profile available. Never suggest nuts, pork, alcohol, "
                "or common allergens. Keep all suggestions halal-safe and allergy-aware by default."
            )

        logger.debug(f"[ProfileContext] build_personalisation_block() complete — block length: {len(block)} chars")
        return block

    def scan_response(self, response: str) -> str:
        """
        Scan the final LLM response for forbidden token violations before returning to user.
        Appends a warning if violations are found. Does not rewrite the response.
        """
        logger.debug(f"[ProfileContext] scan_response() called — scanning {len(response)} chars against {len(self.forbidden)} forbidden tokens")
        violations = []
        response_lower = response.lower()

        for token in self.forbidden:
            if re.search(r'\b' + re.escape(token.lower()) + r'\b', response_lower):
                violations.append(token)

        if violations:
            logger.warning(f"[ProfileContext] scan_response() found {len(violations)} violation(s): {violations}")
            unique_attrs = set(
                self.allergies + [self.diet] + [self.religion]
            )
            # Filter out empty strings
            unique_attrs = [a for a in unique_attrs if a]
            attrs_str = ", ".join(unique_attrs) if unique_attrs else "dietary requirements"
            warning = (
                f"\n\n[Dietary note: Some suggestions above may need review against your "
                f"{attrs_str} requirements before consuming.]"
            )
            return response + warning
        else:
            logger.debug(f"[ProfileContext] scan_response() clean — 0 violations found")

        return response


if __name__ == "__main__":
    import sys
    print("Running ProfileContext self-tests...\n")
    failures = []

    # Test 1 — None profile raises ProfileMissingError
    try:
        ProfileContext(None)
        failures.append("FAIL T1: None profile did not raise ProfileMissingError")
    except ProfileMissingError:
        print("PASS T1: None profile raises ProfileMissingError")

    # Test 2 — Vegan profile forbids chicken and beef
    p = ProfileContext({
        "diet": "vegan",
        "religion": "",
        "allergies": [],
        "dislikes": [],
        "medical_conditions": [],
        "goal": "eat healthier",
        "cooking_level": "novice",
        "calorie_target": 1800
    })
    for token in ["chicken", "beef", "lamb", "egg", "milk", "honey"]:
        if token not in p.forbidden:
            failures.append(f"FAIL T2: '{token}' missing from vegan forbidden set")
    if not any("T2" in f for f in failures):
        print("PASS T2: Vegan forbidden set complete")

    # Test 3 — Muslim profile forbids pork and alcohol
    p = ProfileContext({
        "diet": "balanced",
        "religion": "muslim",
        "allergies": [],
        "dislikes": [],
        "medical_conditions": [],
        "goal": "maintain",
        "cooking_level": "intermediate",
        "calorie_target": 2000
    })
    for token in ["pork", "alcohol", "wine", "beer", "bacon", "lard"]:
        if token not in p.forbidden:
            failures.append(f"FAIL T3: '{token}' missing from Muslim forbidden set")
    if not any("T3" in f for f in failures):
        print("PASS T3: Muslim forbidden set complete")

    # Test 4 — Nut allergy forbids almonds and cashews
    p = ProfileContext({
        "diet": "balanced",
        "religion": "",
        "allergies": ["nuts"],
        "dislikes": [],
        "medical_conditions": [],
        "goal": "maintain",
        "cooking_level": "novice",
        "calorie_target": 2000
    })
    for token in ["almond", "almonds", "cashew", "cashews", "peanut", "peanut butter", "walnut"]:
        if token not in p.forbidden:
            failures.append(f"FAIL T4: '{token}' missing from nut allergy forbidden set")
    if not any("T4" in f for f in failures):
        print("PASS T4: Nut allergy forbidden set complete")

    # Test 5 — filter_csv never returns empty DataFrame
    test_df = pd.DataFrame([{
        "meal_name": "Jollof Rice",
        "core_ingredients": "rice, tomato, onion, pepper",
        "cook_time_minutes": 45
    }])
    p = ProfileContext({
        "diet": "vegan",
        "religion": "muslim",
        "allergies": ["nuts"],
        "dislikes": ["fish"],
        "medical_conditions": ["diabetes"],
        "goal": "lose weight",
        "cooking_level": "novice",
        "calorie_target": 1500
    })
    result = p.filter_csv(test_df)
    if len(result) == 0:
        failures.append("FAIL T5: filter_csv returned empty DataFrame")
    else:
        print("PASS T5: filter_csv never returns empty DataFrame")

    # Test 6 — build_personalisation_block returns non-empty string with key markers
    block = p.build_personalisation_block()
    if not block or len(block.strip()) == 0:
        failures.append("FAIL T6: build_personalisation_block returned empty string")
    for marker in ["ABSOLUTE", "HALAL", "DIABETES", "NOVICE", "STOCK CUBE"]:
        if marker not in block:
            failures.append(f"FAIL T6: '{marker}' missing from personalisation block")
    if not any("T6" in f for f in failures):
        print("PASS T6: Personalisation block contains all required sections")

    # Test 7 — scan_response appends warning when violation present
    p2 = ProfileContext({
        "diet": "vegan",
        "religion": "",
        "allergies": ["nuts"],
        "dislikes": [],
        "medical_conditions": [],
        "goal": "maintain",
        "cooking_level": "novice",
        "calorie_target": 2000
    })
    clean = p2.scan_response("Here is a recipe with tomatoes and lentils.")
    if "[Dietary note" in clean:
        failures.append("FAIL T7: scan_response flagged a clean response")
    else:
        print("PASS T7: Clean response not flagged")
    dirty = p2.scan_response("This recipe uses almonds and cashews for crunch.")
    if "[Dietary note" not in dirty:
        failures.append("FAIL T7b: scan_response missed nut violation")
    else:
        print("PASS T7b: Nut violation correctly flagged")

    # Summary
    print(f"\n{'='*40}")
    if failures:
        print(f"FAILED — {len(failures)} issue(s):")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    else:
        print(f"ALL 7 TESTS PASSED — ProfileContext is ready")
        sys.exit(0)
