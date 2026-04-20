"""
Comprehensive Text Prediction Test Scenarios
Tests various real-world text input scenarios for SVM model
"""

import requests
import json
from typing import List, Dict, Tuple

# Configuration
GATEWAY_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{GATEWAY_URL}/login"
PREDICT_SVM_ENDPOINT = f"{GATEWAY_URL}/predict/svm"

# Test credentials
ADMIN_CREDS = {"username": "admin", "password": "admin"}
USER_CREDS = {"username": "user", "password": "user"}

# Category mappings (8 categories)
CATEGORIES = {
    0: "Livres / Magazines",
    1: "Livres / Magazines",  # Based on test result
    2: "Sports",
    3: "Technologie",
    4: "Mode",
    5: "Cuisine",
    6: "Santé",
    7: "Voyages"
}

# Test scenarios - grouped by expected category
TEST_SCENARIOS = {
    "LIVRES_MAGAZINES": {
        "category": "Livres / Magazines",
        "texts": [
            # Book recommendations
            "Ce livre est super intéressant pour apprendre les sciences",
            "J'ai adoré ce roman de science-fiction, vraiment captivant",
            "Les meilleures histoires pour enfants de cette année",
            "Découvrez les dernières biographies d'écrivains célèbres",
            "Collection complète de manga et bandes dessinées",
            
            # Literature related
            "J'ai lu trois nouveaux livres ce mois-ci, tous excellents",
            "Les classiques de la littérature française sont incontournables",
            "Critique du dernier roman prix Goncourt",
            "Recommandation de lecture pour l'été",
            "Guide complet des éditeurs français indépendants",
            
            # Short/Medium texts
            "Roman policier passionnant",
            "Poésie moderne intéressante",
            "Encyclopédie complète",
            "Atlas géographique détaillé",
            "Dictionnaire multilingue",
        ]
    },
    
    "SPORTS": {
        "category": "Sports",
        "texts": [
            # Football
            "Le PSG a remporté la Ligue 1 cette année, victoire magistrale",
            "Messi est le meilleur joueur de football du siècle",
            "Transferts spectaculaires en football européen",
            "Champions League final était incroyable",
            
            # Other sports
            "Roland Garros 2024: les meilleures performances de tennis",
            "Le cyclisme professionnel, un sport exigeant et passionnant",
            "Marathon annuel dans ma ville, 10000 participants",
            "Judo olympique: techniques et stratégies gagnantes",
            
            # General sports
            "Inscription pour la course à pied locale",
            "Entraînement de fitness trois fois par semaine",
            "Compétition d'athlétisme au niveau national",
            "Tournoi de badminton ce weekend",
            "Vélo de montagne sur les pistes alpines",
        ]
    },
    
    "TECHNOLOGIE": {
        "category": "Technologie",
        "texts": [
            # AI/ML
            "L'intelligence artificielle révolutionne l'industrie",
            "Machine learning et deep learning expliqués simplement",
            "Neural networks pour le traitement du langage naturel",
            "GPT-4 et ses applications dans le monde réel",
            
            # Programming
            "Python est le meilleur langage pour la science des données",
            "Framework FastAPI pour les APIs REST modernes",
            "Docker et Kubernetes pour le déploiement des applications",
            "Git et GitHub pour le contrôle de version",
            
            # General tech
            "Nouveaux gadgets technologiques de 2024",
            "Cybersécurité et protection des données personnelles",
            "Cloud computing: AWS, Azure, Google Cloud",
            "Blockchain et cryptomonnaies expliquées",
            "Réalité virtuelle et augmentée",
        ]
    },
    
    "MODE": {
        "category": "Mode",
        "texts": [
            # Fashion trends
            "Les dernières tendances de mode pour l'été 2024",
            "Vêtements haute couture de Paris Fashion Week",
            "Collection exclusive de designers italiens",
            "Couleurs en vogue cette saison",
            
            # Clothing advice
            "Guide complet pour s'habiller élégamment au bureau",
            "Comment choisir les bonnes chaussures pour chaque occasion",
            "Accessoires indispensables pour une garde-robe complète",
            "Conseils de style pour les femmes de plus de 40 ans",
            
            # General fashion
            "Marques de luxe incontournables",
            "Shopping guide pour hommes modernes",
            "Tendances streetwear urbain",
            "Vêtements durables et éco-responsables",
            "Bijoux et montres de prestige",
        ]
    },
    
    "CUISINE": {
        "category": "Cuisine",
        "texts": [
            # Recipes
            "Recette facile de coq au vin français traditionnel",
            "Comment préparer les meilleurs pâtes à l'italienne",
            "Secrets de la boulangerie artisanale parisienne",
            "Desserts gourmands et faciles à réaliser",
            
            # Cooking techniques
            "Techniques de cuisson profesionnelles expliquées",
            "Les meilleurs couteaux de cuisine pour un chef",
            "Guide complet du vin et accords mets-vins",
            "Nutrition et équilibre dans la cuisine saine",
            
            # Food culture
            "Gastronomie française renommée mondiale",
            "Restaurants avec étoiles Michelin en France",
            "Cuisine méditerranéenne et ses bienfaits",
            "Traditions culinaires des différentes régions",
            "Fruits et légumes de saison",
        ]
    },
    
    "SANTE": {
        "category": "Santé",
        "texts": [
            # Health advice
            "Conseils pour une vie saine et équilibrée",
            "L'importance de l'exercice physique régulier",
            "Nutrition: aliments à favoriser et à éviter",
            "Guide complet du sommeil réparateur",
            
            # Medical topics
            "Les dernières découvertes en médecine",
            "Traitement naturel des maladies courantes",
            "Santé mentale et bien-être psychologique",
            "Prévention des maladies chroniques",
            
            # Wellness
            "Yoga et méditation pour la relaxation",
            "Suppléments vitaminés essentiels",
            "Diète équilibrée pour perdre du poids",
            "Traitement holistique du stress",
            "Exercices de respiration et relaxation",
        ]
    },
    
    "VOYAGES": {
        "category": "Voyages",
        "texts": [
            # Destinations
            "Paris: les meilleures attractions touristiques",
            "Voyage en Thaïlande: guide complet du routard",
            "Croisière en Méditerranée, une expérience inoubliable",
            "Safari en Afrique: les plus beaux parcs nationaux",
            
            # Travel tips
            "Conseils pour voyager pas cher et confortable",
            "Documents nécessaires pour voyager à l'étranger",
            "Meilleures périodes pour visiter différentes régions",
            "Hôtels et auberges recommandées en Europe",
            
            # Adventure
            "Randonnée dans les Alpes françaises",
            "Escalade et alpinisme en montagne",
            "Road trip en Amérique du Nord",
            "Plongée sous-marine en Polynésie",
            "Camping et bivouac en nature",
        ]
    }
}

# Edge cases and special scenarios
EDGE_CASES = {
    "very_short": [
        "Livre",
        "Sport",
        "Code",
        "Mode",
        "Pizza",
        "Hôtel",
    ],
    
    "very_long": [
        "Ce livre extraordinaire sur la science de l'apprentissage machine "
        "explique en détail comment les réseaux de neurones fonctionnent et "
        "comment les appliquer à des problèmes réels. L'auteur, un expert "
        "reconnu dans le domaine, partage ses années d'expérience. Les "
        "chapitres progressent logiquement du théorique au pratique.",
        
        "Le Paris Saint-Germain a remporté un succès éclatant en cette "
        "saison extraordinaire avec les meilleurs joueurs du monde. "
        "Les statistiques montrent une domination totale en ligue 1 et "
        "une performance remarquable en compétition européenne. "
        "Les supporters sont en liesse.",
    ],
    
    "with_special_chars": [
        "Recette: Poulet à l'oignon & citron! Délicieux!",
        "C++ vs Python? Lequel est le meilleur?",
        "J'adore les vacances! #Voyages #Détente",
        "Email: test@example.com pour les infos",
        "Rabais 50% - Promotion limitée!",
    ],
    
    "with_numbers": [
        "2024 sera l'année de la technologie",
        "Le livre contient 500 pages intéressantes",
        "5 raisons de pratiquer le sport",
        "Recette: 200g de farine, 3 œufs, 100ml de lait",
        "Paris est la capitale depuis 1500 ans",
    ],
    
    "mixed_languages": [
        "Le machine learning et l'IA sont l'avenir",
        "Web development avec JavaScript et React",
        "Fashion week à Paris et Milan",
        "Voyage en Thaïlande avec Thai Airways",
    ],
    
    "ambiguous": [
        "J'aime beaucoup les choses",  # Too generic
        "C'est très bien",  # Too generic
        "Ça me plaît",  # Too generic
        "Intéressant et utile",  # Could be any category
    ],
    
    "empty_or_minimal": [
        "",  # Empty
        " ",  # Whitespace only
        ".",  # Just punctuation
        "a",  # Single character
    ]
}


def login(session: requests.Session, credentials: dict) -> bool:
    """Login to the gateway"""
    try:
        response = session.post(LOGIN_ENDPOINT, data=credentials, timeout=5)
        if response.status_code == 200:
            print(f"✅ Logged in as {credentials['username']}")
            return True
        else:
            print(f"❌ Login failed for {credentials['username']}: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False


def predict_text(session: requests.Session, text: str) -> Dict:
    """Make a text prediction"""
    try:
        response = session.post(
            PREDICT_SVM_ENDPOINT,
            json={"text": text},
            timeout=10
        )
        
        if response.status_code == 200:
            return {
                "status": "success",
                "status_code": 200,
                "data": response.json()
            }
        else:
            return {
                "status": "error",
                "status_code": response.status_code,
                "message": response.text
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def print_section(title: str):
    """Print test section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_prediction(text: str, result: Dict, expected_category: str = ""):
    """Print prediction result"""
    if result["status"] == "success":
        data = result["data"]
        label = data.get("label_name", "Unknown")
        confidence = data.get("decision_score", [])
        
        expected = f" (Expected: {expected_category})" if expected_category else ""
        match = "✅" if expected_category and label == expected_category else "❓" if expected_category else "📊"
        
        print(f"{match} Text: {text[:60]}...")
        print(f"   → Predicted: {label}{expected}")
        if confidence:
            print(f"   → Confidence scores: {len(confidence)} features")
        print()
    else:
        print(f"❌ Text: {text[:60]}...")
        print(f"   → Error: {result.get('message', 'Unknown error')}\n")


def test_category_scenarios():
    """Test organized scenarios by category"""
    print_section("📝 TEST 1: CATEGORY-SPECIFIC SCENARIOS")
    
    session = requests.Session()
    if not login(session, USER_CREDS):
        return
    
    total_correct = 0
    total_tests = 0
    
    for category_key, scenario in TEST_SCENARIOS.items():
        category_name = scenario["category"]
        print(f"\n🎯 {category_name.upper()}")
        print(f"   Testing {len(scenario['texts'])} examples...\n")
        
        category_correct = 0
        
        for text in scenario["texts"]:
            result = predict_text(session, text)
            total_tests += 1
            
            if result["status"] == "success":
                predicted_label = result["data"].get("label_name", "Unknown")
                if predicted_label == category_name:
                    category_correct += 1
                    total_correct += 1
                    print_prediction(text, result, category_name)
                else:
                    print_prediction(text, result, category_name)
            else:
                print_prediction(text, result, category_name)
        
        accuracy = (category_correct / len(scenario["texts"]) * 100) if scenario["texts"] else 0
        print(f"   Category accuracy: {category_correct}/{len(scenario['texts'])} ({accuracy:.1f}%)\n")


def test_edge_cases():
    """Test edge cases"""
    print_section("⚠️  TEST 2: EDGE CASES & SPECIAL SCENARIOS")
    
    session = requests.Session()
    if not login(session, USER_CREDS):
        return
    
    for case_type, texts in EDGE_CASES.items():
        print(f"\n📌 {case_type.upper()}")
        print(f"   Testing {len(texts)} examples...\n")
        
        for text in texts:
            result = predict_text(session, text)
            display_text = text if len(text) > 0 else "[EMPTY]"
            print_prediction(display_text, result)


def test_batch_predictions():
    """Test batch of predictions and analyze patterns"""
    print_section("🔄 TEST 3: BATCH PREDICTIONS & PATTERN ANALYSIS")
    
    session = requests.Session()
    if not login(session, USER_CREDS):
        return
    
    # Collect predictions for all scenarios
    all_predictions = []
    
    print("📊 Running batch predictions...\n")
    
    for category_key, scenario in TEST_SCENARIOS.items():
        for text in scenario["texts"]:
            result = predict_text(session, text)
            if result["status"] == "success":
                all_predictions.append({
                    "text": text,
                    "expected": scenario["category"],
                    "predicted": result["data"].get("label_name", "Unknown"),
                    "scores": result["data"].get("decision_score", [])
                })
    
    # Analyze results
    if not all_predictions:
        print("❌ No predictions collected")
        return
    
    print(f"✅ Collected {len(all_predictions)} predictions\n")
    
    # Calculate accuracy per category
    print("📈 ACCURACY BY CATEGORY:\n")
    category_stats = {}
    
    for pred in all_predictions:
        expected = pred["expected"]
        if expected not in category_stats:
            category_stats[expected] = {"correct": 0, "total": 0}
        
        category_stats[expected]["total"] += 1
        if pred["predicted"] == expected:
            category_stats[expected]["correct"] += 1
    
    total_accuracy = 0
    for category, stats in sorted(category_stats.items()):
        accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        total_accuracy += accuracy
        
        bar_length = int(accuracy / 5)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        print(f"  {category:20} {bar} {stats['correct']:2}/{stats['total']:2} ({accuracy:5.1f}%)")
    
    overall = (total_accuracy / len(category_stats)) if category_stats else 0
    print(f"\n  Overall Accuracy: {overall:.1f}%")
    
    # Confusion matrix
    print("\n\n📊 CONFUSION MATRIX:\n")
    print(f"{'Expected':<20} {'Predicted':<20} {'Count':<8}")
    print("-" * 48)
    
    confusion = {}
    for pred in all_predictions:
        key = (pred["expected"], pred["predicted"])
        confusion[key] = confusion.get(key, 0) + 1
    
    for (expected, predicted), count in sorted(confusion.items()):
        if expected != predicted:  # Show only misclassifications
            print(f"{expected:<20} {predicted:<20} {count:<8}")


def test_concurrent_predictions():
    """Test predictions from both user and admin"""
    print_section("👥 TEST 4: MULTI-USER PREDICTIONS")
    
    # Create two sessions
    user_session = requests.Session()
    admin_session = requests.Session()
    
    print("🔑 Creating sessions...")
    user_ok = login(user_session, USER_CREDS)
    admin_ok = login(admin_session, ADMIN_CREDS)
    
    if not user_ok or not admin_ok:
        return
    
    test_texts = [
        ("Ce livre sur l'histoire est magnifique", "Livres / Magazines"),
        ("Quel match de football intense", "Sports"),
        ("Les nouvelles technologies changent tout", "Technologie"),
    ]
    
    print("\n🔄 Running concurrent predictions...\n")
    
    for text, expected in test_texts:
        print(f"📝 Text: {text}")
        
        user_result = predict_text(user_session, text)
        admin_result = predict_text(admin_session, text)
        
        print(f"   User:  {user_result['data'].get('label_name', 'Error') if user_result['status'] == 'success' else 'Error'}")
        print(f"   Admin: {admin_result['data'].get('label_name', 'Error') if admin_result['status'] == 'success' else 'Error'}")
        print()


def test_text_variations():
    """Test variations of same concept"""
    print_section("🔄 TEST 5: TEXT VARIATIONS & ROBUSTNESS")
    
    session = requests.Session()
    if not login(session, USER_CREDS):
        return
    
    # Variations of book-related text
    variations = [
        ("Livre", "Minimal"),
        ("Je lis un livre", "Simple"),
        ("Je suis en train de lire un livre très intéressant", "Medium"),
        ("Ce livre fascinant sur la science propose une analyse profonde des phénomènes naturels", "Verbose"),
        ("LIVRE", "UPPERCASE"),
        ("livre", "lowercase"),
        ("LiVrE", "MixedCase"),
    ]
    
    print("📚 BOOK VARIATIONS:\n")
    
    results_map = {}
    for text, variant_type in variations:
        result = predict_text(session, text)
        if result["status"] == "success":
            label = result["data"].get("label_name", "Unknown")
            results_map[variant_type] = label
            print(f"✅ {variant_type:12} → {label}")
        else:
            print(f"❌ {variant_type:12} → Error")
    
    # Check consistency
    consistent = len(set(results_map.values())) == 1
    if consistent:
        print("\n✅ All variations predicted consistently!")
    else:
        print("\n⚠️  Predictions vary by text variation")


def main():
    """Run all text prediction scenario tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  TEXT PREDICTION COMPREHENSIVE SCENARIO TESTS".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    
    print(f"\n🔗 Gateway: {GATEWAY_URL}")
    print(f"🎯 Endpoint: {PREDICT_SVM_ENDPOINT}")
    print(f"📊 Test Scenarios: {sum(len(s['texts']) for s in TEST_SCENARIOS.values())} examples")
    print(f"⚠️  Edge Cases: {sum(len(t) for t in EDGE_CASES.values())} examples")
    
    # Run tests
    test_category_scenarios()
    test_edge_cases()
    test_batch_predictions()
    test_concurrent_predictions()
    test_text_variations()
    
    # Summary
    print("\n\n" + "="*80)
    print("  ALL TEXT PREDICTION SCENARIO TESTS COMPLETED")
    print("="*80)
    print("\n✅ Test Coverage:")
    print(f"   • {sum(len(s['texts']) for s in TEST_SCENARIOS.values())} category-specific texts")
    print(f"   • {sum(len(t) for t in EDGE_CASES.values())} edge case variations")
    print(f"   • Multi-user concurrent predictions")
    print(f"   • Text variation robustness")
    print(f"   • Batch prediction analysis")
    print("\n📊 Analysis includes:")
    print(f"   • Per-category accuracy metrics")
    print(f"   • Confusion matrix")
    print(f"   • Model consistency checks")
    print(f"   • Prediction patterns")


if __name__ == "__main__":
    main()
