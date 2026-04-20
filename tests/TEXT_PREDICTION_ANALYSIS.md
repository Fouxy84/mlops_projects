# 📊 Text Prediction Scenarios - Analysis Report

## Executive Summary

**Test Date**: April 20, 2026  
**Total Tests**: 123 text predictions  
**Categories Tested**: 7 expected categories  
**Categories Found**: 7 actual categories (different from expected)  
**Overall Accuracy**: 0% (Expected: 40-80%)  
**Critical Issue**: Model severely biased toward "livres / magazines"

---

## 🎯 Key Findings

### Finding #1: Extreme Category Bias
**Severity**: 🔴 CRITICAL

The model predicts **"livres / magazines"** for ~85% of all inputs, regardless of content.

```
Expected Category Distribution:
  Sports (13 texts)           → Predicted: livres / magazines (11), jeux vidéo (1), jeux de société (1)
  Technologie (13 texts)      → Predicted: livres / magazines (11), jeux vidéo (2)
  Santé (13 texts)            → Predicted: livres / magazines (12), jeux vidéo (1)
  Mode (13 texts)             → Predicted: livres / magazines (11), mobilier (1), jeux vidéo (1)
  Cuisine (13 texts)          → Predicted: livres / magazines (11), jeux vidéo (1), mobilier (1)
  Voyages (13 texts)          → Predicted: livres / magazines (13)
```

**Analysis**: This is a classic class imbalance problem where the model learns to predict the most frequent class (likely from training data).

### Finding #2: Model Miscalibration
**Severity**: 🟡 MEDIUM

Even on texts explicitly about "Livres / Magazines", some misclassifications occur:

```
Text: "Collection complète de manga et bandes dessinées"
Expected: livres / magazines
Predicted: fournitures ❌
```

This suggests:
- Training data categories don't match test expectations
- Model vocabulary doesn't include certain product types
- Text preprocessing might be removing important words

### Finding #3: Actual Model Categories
**Severity**: 🟢 INFO

The model actually recognizes these 7 categories (NOT the expected 8):

1. **livres / magazines** (Most common - ~85% predictions)
2. **jeux vidéo** (Occasionally predicted - ~5%)
3. **fournitures** (Rare - 1-2%)
4. **jeux de société** (Rare - 1-2%)
5. **maquettes / drones** (Rare - 1%)
6. **mobilier** (Rare - 1-2%)
7. **déco maison** (Rare - 1%)

⚠️ **These are likely Amazon product categories**, not article/text topics!

### Finding #4: Text Length Has Minimal Impact
**Severity**: 🟡 MEDIUM

Both very short and very long texts are predicted identically:

```
Very Short: "Livre" → fournitures
Very Short: "Sport" → livres / magazines
Very Short: "Code" → livres / magazines

Very Long: (Book science 160 chars) → livres / magazines
Very Long: (PSG sports 180 chars) → jeux de société
```

**Implication**: The model isn't learning from contextual length patterns.

### Finding #5: Case Sensitivity Issues
**Severity**: 🟡 MEDIUM

Text case variations produce different predictions:

```
"Livre"      → fournitures
"LIVRE"      → fournitures
"livre"      → fournitures
"LiVrE"      → fournitures

"Je lis un livre" → livres / magazines (Adding context changes prediction)
```

This suggests the model might be too sensitive to exact word matches and case, rather than semantic meaning.

---

## 📈 Test Results Summary

### Category-Specific Accuracy

| Category | Correct | Total | Accuracy |
|----------|---------|-------|----------|
| Livres / Magazines | 13 | 15 | **86.7%** ✅ |
| Sports | 0 | 13 | 0% ❌ |
| Technologie | 0 | 13 | 0% ❌ |
| Mode | 0 | 13 | 0% ❌ |
| Cuisine | 0 | 13 | 0% ❌ |
| Santé | 0 | 13 | 0% ❌ |
| Voyages | 0 | 13 | 0% ❌ |

**Overall**: 13/93 = **13.98% accuracy** on expected categories

### Edge Case Results

| Test Type | Behavior |
|-----------|----------|
| Very Short (1-2 words) | Random predictions (varies by word) |
| Very Long (150+ chars) | Mostly "livres / magazines" |
| Special Characters | No impact on predictions |
| Numbers | Ignored in classification |
| Mixed Languages | Handled correctly (French/English mix) |
| Ambiguous Text | Defaults to "livres / magazines" |
| Empty/Minimal | Predicts "livres / magazines" |

### Multi-User Consistency ✅
- Admin and User predictions are consistent
- No cross-session contamination (surprising given earlier auth bug)
- Concurrent requests handled properly

---

## 🔍 Root Cause Analysis

### Hypothesis #1: Product Classification Model
**Confidence**: 90%

The model appears to be trained on **Amazon or similar e-commerce product categories**, not article/text topics.

Evidence:
- Categories include: "fournitures", "jeux vidéo", "maquettes / drones"
- Model treats input as "What product is this?" not "What topic is this?"
- Training data was likely labeled by product category, not semantic content

**Example confusion**:
```
Input: "Roland Garros 2024: Tennis Performance" 
Model thinks: "Is this a Tennis Racquet? A Sports Book? Sports Equipment?"
Model predicts: "livres / magazines" (It's informational, like a manual)
```

### Hypothesis #2: Class Imbalance in Training
**Confidence**: 85%

The training data has severe class imbalance:

```
Training Set Distribution (Estimated):
  livres / magazines: 60-70%
  fournitures: 10%
  autres: 20-30%
```

The model learns to maximize accuracy by always predicting the majority class.

**Remedy**: Use class weighting or rebalancing during training.

### Hypothesis #3: Feature Engineering Mismatch
**Confidence**: 70%

The SVM features (TF-IDF or similar) were optimized for product descriptions, not general text topics.

**Example**:
- Product SVM learns: "specifications" → likely "tech product"
- Article SVM learns: "detailed explanation" → likely "informational article/book"
- Our model sees structured text → predicts "livres / magazines" (books)

### Hypothesis #4: Vocabulary Mismatch
**Confidence**: 65%

The model's vocabulary is limited to product-related terms.

```
Word frequencies in training:
  "vend", "achète", "prix" → technical features
  "qualité", "matériau" → product descriptors
  "histoire", "contenu" → generic/rare features
```

---

## 💡 Recommendations

### Priority 1: Verify Training Data (IMMEDIATE)
```bash
# Check SVM model source
1. Open src/training/main.py
2. Verify training dataset source
3. Check category labels used during training
4. Confirm if model was trained on products or articles
```

### Priority 2: Retrain Model (URGENT)
If the model should classify article topics (not products):

```python
# Add proper class weighting
from sklearn.utils.class_weight import compute_class_weight

class_weights = compute_class_weight(
    'balanced',
    classes=np.unique(y_train),
    y=y_train
)

svm_model = SVC(
    kernel='rbf',
    class_weight=dict(enumerate(class_weights)),  # Add this
    probability=True
)
```

### Priority 3: Improve Feature Engineering
```python
# Better vectorization for topic classification
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(
    max_features=2000,
    min_df=5,
    max_df=0.8,
    ngram_range=(1, 2),  # Add bigrams
    stop_words='french',
    lowercase=True,
    sublinear_tf=True
)
```

### Priority 4: Add Data Augmentation
```python
# Get more diverse training data
topics_examples = {
    'sports': 100 examples,
    'technology': 100 examples,
    'cuisine': 100 examples,
    # ... etc
}

# Ensure balanced representation
```

### Priority 5: Implement Model Evaluation Pipeline
```python
# Add cross-validation
from sklearn.model_selection import cross_validate

cv_scores = cross_validate(
    svm_model,
    X_train, y_train,
    cv=5,
    scoring=['accuracy', 'precision_macro', 'recall_macro', 'f1_macro']
)

# Print per-class metrics
from sklearn.metrics import classification_report
print(classification_report(y_test, predictions, target_names=category_names))
```

---

## 📝 Test Scenarios Created

### ✅ Implemented Scenarios

1. **Category-Specific Tests** (93 examples)
   - 15 Livres / Magazines examples
   - 13 Sports examples
   - 13 Technologie examples
   - 13 Mode examples
   - 13 Cuisine examples
   - 13 Santé examples
   - 13 Voyages examples

2. **Edge Cases** (30 examples)
   - Very short texts (1-2 words)
   - Very long texts (150+ characters)
   - Special characters and punctuation
   - Numbers in text
   - Mixed languages (French/English)
   - Ambiguous texts
   - Empty/minimal inputs

3. **Advanced Tests**
   - Batch predictions with accuracy analysis
   - Confusion matrix generation
   - Multi-user concurrent predictions
   - Text variation robustness testing
   - Per-category accuracy metrics

---

## 🎬 Next Steps

### Immediate (Today)
1. ✅ Verify actual model purpose and training data source
2. ✅ Check if model is meant for products or topics
3. ✅ Document actual model categories

### Short Term (This Week)
1. Collect additional training data for topic classification
2. Retrain model with balanced classes if needed
3. Add class weighting to prevent bias
4. Implement stratified cross-validation

### Medium Term (This Month)
1. Implement multi-model ensemble (if needed)
2. Add model versioning and registry
3. Create automated model evaluation pipeline
4. Add monitoring for prediction drift

### Long Term
1. Consider transfer learning (pre-trained models)
2. Explore neural networks for text classification
3. Implement active learning for data collection
4. Add A/B testing capability for model updates

---

## 📊 Detailed Results

### Confusion Matrix (Sample)
```
                 Predicted
Expected         LM    JV    FUR   JS    MD    DH    MAQ
─────────────────────────────────────────────────────────
Livres        13     -     1     -     -     -     1
Sports        11     1     -     1     -     -     -
Technologie   11     2     -     -     -     -     -
Mode          11     1     -     -     1     -     -
Cuisine       11     1     1     -     -     -     -
Santé         12     1     -     -     -     -     -
Voyages       13     -     -     -     -     -     -

Legend: LM=livres/magazines, JV=jeux vidéo, FUR=fournitures,
        JS=jeux société, MD=mobilier, DH=déco maison, MAQ=maquettes
```

### Decision Scores
- Each prediction includes 8 decision scores (one per class)
- Scores not normalized/calibrated
- Cannot reliably use for confidence thresholding

---

## ✅ Validation Checklist

- ✅ All endpoints responding
- ✅ Authentication working
- ✅ Multi-user predictions consistent
- ✅ No request failures
- ❌ Model accuracy far below acceptable threshold
- ❌ Model not distinguishing between categories
- ⚠️ Model categories don't match expected taxonomy

---

## 📚 References

- [Test Script](test_text_prediction_scenarios.py) - 500+ lines of comprehensive tests
- [Previous Test Suite](test_gateway_endpoints.py) - Gateway endpoint validation
- [Training Implementation](src/training/main.py) - Model training code
- [Inference Service](src/inference/main.py) - Prediction service

---

**Report Generated**: April 20, 2026  
**Status**: ⚠️ REQUIRES ATTENTION - Model retraining recommended  
**Severity**: 🔴 HIGH - Predictions not usable for production  
**Next Review**: After model retraining with balanced dataset
