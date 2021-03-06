# -*- coding: utf-8 -*-
"""linear_algebra_PCA_analysis_plot

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1cQKV3Sip4qN_dT2tHPuV3L6ouQjOYr32

**Import** **libraries**
"""

from re import X
import numpy as np
import csv
from numpy.core.defchararray import encode
from numpy.core.numeric import NaN
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix,  f1_score
from sklearn.preprocessing import Normalizer
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings("ignore")

"""**Read Data**"""

import pandas as pd 
def data_loader(train_path, test_path):
    data = pd.read_csv(train_path)
    data_top = list(data.columns)
    with open(train_path, 'r') as fp:     
        data_train = list(csv.reader(fp))
        train_id = np.array(data_train[1:])[:, :1]
        data_train = np.array(data_train[1:])[:, 1:]
        
    with open(test_path, 'r') as fp:     
        data_test = list(csv.reader(fp))
        test_id = np.array(data_test[1:])
        data_test = np.array(data_test[1:])[:, 1:]
        
    
    return data_train, train_id, data_test, test_id,data_top

"""**Encode Y**"""

def encode_y(data):
    from sklearn.preprocessing import OrdinalEncoder
    enc = OrdinalEncoder(categories=[['No Churn', 'Competitor', 'Dissatisfaction', 'Attitude', 'Price', 'Other']])
    y = enc.fit_transform(data[:, 44:45])
    for i in range((len(y))):
        y[i] = int(y[i])
    return y

"""**Encode Other Features**"""

def encode_other(data, feats):
    from sklearn.preprocessing import OrdinalEncoder
    enc = OrdinalEncoder()
    for i in feats:
        data[:, i:i+1] = enc.fit_transform(data[:, i:i+1]) # 35 contract
    return data

"""**Extract Numerical Features**"""

def feature_extractor(data_trainval, data_test, feats,bb):
    x = data_trainval[:, feats]
    x = (x.astype(np.float))
    #x = np.nan_to_num(x)

    x_test = data_test[:, feats]
    x_test = (x_test.astype(np.float))
    if bb==1:
      x = np.nan_to_num(x)
      x_test = np.nan_to_num(x_test)
           
    elif bb==2: #nan as avg 
      
      xmean = np.mean(np.nan_to_num(x), dtype=np.float64)
      x_testmean = np.mean(np.nan_to_num(x_test), dtype=np.float64)
      where_are_NaNs = np.where(np.isnan(x))
      x[where_are_NaNs] = xmean
      where_are_NaNst = np.where(np.isnan(x_test))
      x_test[where_are_NaNst] = x_testmean
    elif bb==3: #nan as a new type      
      where_are_NaNs = np.where(np.isnan(x))
      x[where_are_NaNs] = 666
      where_are_NaNst = np.where(np.isnan(x_test))      
      x_test[where_are_NaNst] = 666
    

    return x, x_test

"""**Normalize**"""

def normalize(data_trainval, data_test):
    scaler = Normalizer().fit(data_trainval)
    data_trainval = scaler.transform(data_trainval)
    scaler = Normalizer().fit(data_test)
    data_test = scaler.transform(data_test)
    return data_trainval, data_test

"""**Beta Encoder**"""

class BetaEncoder(object):

  def __init__(self, group):
    self.group = group
    self.stats = None

  def fit(self, X_train, target_col):
    self.prior_mean = np.mean(X_train[target_col])
    stats = X_train[[target_col, self.group]].groupby(self.group)
    stats = stats.agg(['sum', 'count'])[target_col]    
    stats.rename(columns={'sum': 'n', 'count': 'N'}, inplace=True)
    stats.reset_index(level=0, inplace=True)           
    self.stats = stats

  def transform(self, X_train, stat_type, N_min=1):
        
    X_train_stats = np.hstack(X_train[[self.group]], self.stats, how='left')
    n = X_train_stats['n'].copy()
    N = X_train_stats['N'].copy()
    
    # fill in missing
    nan_indexs = np.isnan(n)
    n[nan_indexs] = self.prior_mean
    N[nan_indexs] = 1.0
    
    # prior parameters
    N_prior = np.maximum(N_min-N, 0)
    alpha_prior = self.prior_mean*N_prior
    beta_prior = (1-self.prior_mean)*N_prior
    
    # posterior parameters
    alpha = alpha_prior + n
    beta =  beta_prior + N-n
    
    # calculate statistics
    if stat_type=='mean':
        num = alpha
        dem = alpha+beta
                
    elif stat_type=='mode':
        num = alpha-1
        dem = alpha+beta-2
        
    elif stat_type=='median':
        num = alpha-1/3
        dem = alpha+beta-2/3
    
    elif stat_type=='var':
        num = alpha*beta
        dem = (alpha+beta)**2*(alpha+beta+1)
                
    elif stat_type=='skewness':
        num = 2*(beta-alpha)*np.sqrt(alpha+beta+1)
        dem = (alpha+beta+2)*np.sqrt(alpha*beta)

    elif stat_type=='kurtosis':
        num = 6*(alpha-beta)**2*(alpha+beta+1) - alpha*beta*(alpha+beta+2)
        dem = alpha*beta*(alpha+beta+2)*(alpha+beta+3)

    else:
        num = self.prior_mean
        dem = np.ones_like(N_prior)
        
    # replace missing
    value = num/dem
    value[np.isnan(value)] = np.nanmedian(value)
    return value

"""**Upsampling**"""

def upsampling(X_train, y_train):
  # upsampling on training data only
  from imblearn.over_sampling import SMOTE
  smt = SMOTE(random_state = 1126)
  X_train, y_train = smt.fit_resample(X_train, y_train)
  from collections import Counter
  print(sorted(Counter(y_train).items()))
  return X_train, y_train

"""**Undersampling**"""

def undersampling(X_train, y_train):
  # downsampling on data only
  from imblearn.under_sampling import RandomUnderSampler
  rus = RandomUnderSampler(random_state=1126)
  X_train, y_train = rus.fit_resample(X_train, y_train)
  from collections import Counter
  print(sorted(Counter(y_train).items()))
  return X_train, y_train

"""**Naive Bayes classifier**"""

def NB(X_train, X_val, y_train, y_val):
    from sklearn.naive_bayes import GaussianNB
    gnb = GaussianNB().fit(X_train, y_train)
    val_predictions = gnb.predict(X_val)

    # Validation accuracy
    accuracy = gnb.score(X_val, y_val)
    print('NB accuracy')
    print(accuracy)
    # Validation confusion matrix
    cm = confusion_matrix(y_val, val_predictions)
    print('NB CFmap')
    print(cm)

    #testing
    test_predictions = gnb.predict(x_test)
    return test_predictions

"""**KNN**"""

def KNN(X_train, X_val, y_train, y_val):
    from sklearn.neighbors import KNeighborsClassifier
    knn = KNeighborsClassifier(n_neighbors = 7).fit(X_train, y_train)
    # model accuracy for X_test 
    accuracy = knn.score(X_val, y_val)
    print('KNN accuracy')
    print(accuracy)
    # creating a confusion matrix
    knn_predictions = knn.predict(X_val)
    cm = confusion_matrix(y_val, knn_predictions)
    print('KNN CFmap')
    print(cm)
    #testing
    test_predictions = knn.predict(x_test)
    return test_predictions

"""**SVM**"""

def SVM(X_train, X_val, y_train, y_val, grid = False):
    from sklearn.svm import SVC
    
    # grid search
    if grid == True:
        svm = SVC()
        parameters = {'kernel':['rbf'],
                    'gamma': [ 1e-4, 1e-3, 1e-2], #, 1e-1, 1
                    'C': [2e7, 2e8, 2e9, 2e10, 2e11, 2e12, 2e13], #
                    }
        clf = GridSearchCV(svm, parameters)#  scoring=['recall_macro', 'precision_macro'], refit=False
        clf.fit(X_train, y_train)
        print(clf.best_params_)
        svm = clf.best_estimator_
    
    if grid == False:
        svm = SVC(kernel = 'rbf', C = 1)
        svm.fit(X_train, y_train)

    svm_predictions = svm.predict(X_val)
    accuracy = svm.score(X_val, y_val)
    print('SVM accuracy')
    print(accuracy)
    cm = confusion_matrix(y_val, svm_predictions)
    print('SVM CFmap')
    print(cm)
    print('RF f1 score')
    print(f1_score(y_val, svm_predictions, average = 'macro'))
    #testing
    test_predictions = svm.predict(x_test)
    return test_predictions

"""**Random Forest**"""

def RF(X_train, X_val, y_train, y_val, grid = False):
    from sklearn.ensemble import RandomForestClassifier

    #grid search
    if grid == True:
        rf = RandomForestClassifier()
        parameters = {'n_estimators':range(100, 1000, 100)}
        clf = GridSearchCV(rf, parameters)
        clf.fit(X_train, y_train)
        rf = clf.best_estimator_

    if grid == False:
        rf = RandomForestClassifier()
        rf.fit(X_train, y_train)
    
    #result
    rf_predictions = rf.predict(X_val)
    accuracy = rf.score(X_val, y_val)
    print('RF accuracy')
    print(accuracy)
    cm = confusion_matrix(y_val, rf_predictions)
    print('RF CFmap')
    print(cm)
    print('RF f1 score')
    print(f1_score(y_val, rf_predictions, average = 'macro'))
    #testing
    test_predictions = rf.predict(x_test)
    return test_predictions

"""**Gradient Boost**"""

def GradientBoosting(X_train, X_val, y_train, y_val, grid = False):
    from sklearn.ensemble import GradientBoostingClassifier

    if grid == True:
        gb = GradientBoostingClassifier()
        parameters = {'n_estimators': range(100, 500, 100),
                      'learning_rate': [0.01, 0.05, 0.1, 0.5, 1]
                      }
        clf = GridSearchCV(gb, parameters)
        clf.fit(X_train, y_train)
        print(clf.best_params_)
        gb = clf.best_estimator_

    else:
        gb = GradientBoostingClassifier(n_estimators = 100, learning_rate = 0.1, random_state = 1126)
        gb = Pipeline([ #('pca', PCA(n_components = 5)),
                        ('clf', gb)
                    ])
        gb.fit(X_train, y_train)

    # Validation
    accuracy = gb.score(X_val, y_val)
    print('GB accuracy')
    print(accuracy)
    # creating a confusion matrix
    gb_predictions = gb.predict(X_val)
    cm = confusion_matrix(y_val, gb_predictions)
    print('GB CFmap')
    print(cm)
    print('GB f1 score')
    print(f1_score(y_val, gb_predictions, average = 'macro'))
    # add validation-set into sub-training set
    X_trainval = np.vstack((np.array(X_train), np.array(X_val)))
    y_trainval = np.hstack((np.array(y_train), np.array(y_val)))

    # retraining w/ full training set
    if grid == True:
        gb = GradientBoostingClassifier(clf.best_params_)
    else:
        gb = GradientBoostingClassifier(n_estimators = 400, learning_rate = 0.5, random_state = 1126)

    gb.fit(X_trainval, y_trainval)
    # testing
    test_predictions = gb.predict(x_test)
    return test_predictions

"""**Output Prediction**"""

def make_pred(pred, test_id):
    with open('pred.csv', 'w', newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow(['Customer ID', 'Churn Category'])
        for i, p in enumerate(pred): 
            writer.writerow([test_id[i, 0], int(p)])

"""**Download Data**"""

train_path = 'data.train.csv'  # path to training data
test_path = 'data.test.csv'
!gdown --id '1_umR9yNNBZLYourueYsPGeLR7IQLOuy1' --output data.train.csv
!gdown --id '1Q-8zWSrDT8eDlQfDGup2LSIQ0RwMvLg_' --output data.test.csv

"""**Main**"""

# Feature Extraction with RFE
from pandas import read_csv
from sklearn.feature_selection import RFE
from sklearn.linear_model import LogisticRegression
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import f_classif
from numpy import set_printoptions
from sklearn.datasets import load_digits
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.feature_selection import SelectFromModel
from sklearn.linear_model import LogisticRegression
from sklearn.feature_selection import RFE
import pandas as pd

data_trainval, train_id, data_test, test_id ,feature_names = data_loader(train_path,test_path)
feanames = []
for i in range(len(feature_names)-1):
  feanames.append(feature_names[i+1])


y = np.ravel(encode_y(data_trainval))
# encode non-float data
#data_trainval = encode_other(data_trainval,  list(range(0,44)))
#data_test = encode_other(data_test, list(range(0,44)))

data_trainval = encode_other(data_trainval, [1,8,9,10,12,14,16,17,20,21,23,24,25]+list(range(3,7))+list(range(27,38)))
data_test = encode_other(data_test,[1,8,9,10,12,14,16,17,20,21,23,24,25]+list(range(3,7))+list(range(27,38)))

# feature extraction - non-label
# 2-Ages, 19-Tenure_in_Months, 22-Avg_Monthly_Long_Distance_Charges
# 38-Monthly_Charge, 39-Total_Charges...43 money-related data
x_trainval, x_test = feature_extractor(data_trainval, data_test, list(range(0,44)),1)
#x_trainval, x_test = feature_extractor(data_trainval, data_test, [1,2,10,19,22]+list(range(38,43)),3)

# do normalization
#x_trainval, x_test = normalize(x_trainval, x_test)

# feature extraction - non-float
# 15-Satisfication_Score, 18-Number of Referrals, 20-Offer, 21-Phone_Service, 35-contract (2-Ages improve here, but not on kaggle)
#x_trainval_la, x_test_la = feature_extractor(data_trainval, data_test,  list(range(0,44)))
#x_trainval_la, x_test_la = feature_extractor(data_trainval, data_test,  [7,15,18,20,21,24,25,26,27,28,29,30,34,35],3)
#x_trainval = np.hstack((x_trainval, x_trainval_la))
#x_test = np.hstack((x_test, x_test_la))
#print(x_trainval)
#print(x_test)

df = pd.DataFrame(x_trainval)

'''
import matplotlib.pyplot as plt
import seaborn as sns
f = plt.figure(figsize=(44, 44))
corr = df.corr()
plt.matshow(df.corr(), fignum=f.number)
corr.style.background_gradient(cmap='coolwarm')
plt.xticks(range(df.select_dtypes(['number']).shape[1]), df.select_dtypes(['number']).columns, fontsize=30, rotation=45)
plt.yticks(range(df.select_dtypes(['number']).shape[1]), df.select_dtypes(['number']).columns, fontsize=30)
cb = plt.colorbar(cmap='coolwarm')
cb.ax.tick_params(labelsize=30)
plt.title('Correlation Matrix', fontsize=50);
'''

dataA = df
import math
import matplotlib.pyplot as plt

for i in range(44):
  dataA[i]-=dataA[i].mean()

print("dataA",dataA)

A = dataA.to_numpy()
print("dataA",dataA)
print("A",A)
covarianceMatrix = ((A.T).dot(A))/4225
covarianceDf = pd.DataFrame(covarianceMatrix)

print("sigma",covarianceDf)

f = plt.figure(figsize=(43, 43))
plt.matshow(covarianceDf, fignum=f.number)
covarianceDf.style.background_gradient(cmap='coolwarm')
plt.xticks(range(df.select_dtypes(['number']).shape[1]), df.select_dtypes(['number']).columns, fontsize=30, rotation=45)
plt.yticks(range(df.select_dtypes(['number']).shape[1]), df.select_dtypes(['number']).columns, fontsize=30)
cb = plt.colorbar(cmap='coolwarm')
cb.ax.tick_params(labelsize=30)
plt.title('covariance Matrix', fontsize=50);

dataB = dataA
for i in range(44):
  dataB[i]/=math.sqrt(dataB[i].var())

print("dataB",dataB)
#dataA.to_excel(excel_writer = "MatrixA.xlsx")
#dataB.to_excel(excel_writer = "MatrixB.xlsx")
B = dataB.to_numpy()


print("dataA",dataA)
correlationMatrix = ((B.T).dot(B))/4225
correlationDf = pd.DataFrame(correlationMatrix)

print("sigma",covarianceDf)
print("rpo",correlationDf)


#covarianceDf.to_excel(excel_writer = "covariance_Matrix.xlsx")
#correlationDf.to_excel(excel_writer = "correlation_Matirx.xlsx")



def find_max(matrix):
  maximum = float('-inf')
  index_max = 0
  for i in range(len(matrix)):
    if matrix[i] > maximum:
      maximum = matrix[i]
      index_max = (i+1)
  return index_max, maximum

from numpy import linalg as LA
BTB = B.T.dot(B)
eigenvalues, eigenvecors = LA.eig(BTB)
first_evalue = eigenvalues[0]
first_evector = eigenvecors[0]
second_evalue = eigenvalues[1]
second_evector = eigenvecors[1]
print("??1 = ",first_evalue)
print("v1 = ",first_evector)
print("??2 = ",second_evalue)
print("v2 = ",second_evector)
print(LA.norm(first_evector))
print(LA.norm(second_evector))

MM = (first_evector.T).dot(B.T)
MM1 = MM.dot(B)
e1TBTBe1 = MM1.dot(first_evector)
print(e1TBTBe1)

MM2 = (second_evector.T).dot(B.T)
MM21 = MM2.dot(B)
e2TBTBe2 = MM21.dot(second_evector)
print(e2TBTBe2)

'''
index_z1max_index = find_max(z1)[0]
index_z1max = find_max(z1)[1]

print(z1)
print(index_z1max_index)
print(index_z1max)

index_z2max_index = find_max(z2)[0]
index_z2max = find_max(z2)[1]

print(z2)
print(index_z2max_index)
print(index_z2max)
'''



'''
test = SelectKBest(score_func=f_classif, k=3)
fit = test.fit(x_trainval, y)
# summarize scores
set_printoptions(precision=3)
print(fit.scores_)
print(fit.get_support())
for i in range(len(fit.get_support())):
  if(fit.get_support()[i]==True):
    print(i," ",df.columns[i+1])
x_trainval = fit.transform(x_trainval)
x_test = fit.transform(x_test)
'''

#checked
# f_class
'''
test = SelectKBest(score_func=f_classif, k=8)
fit = test.fit(x_trainval, y)
# summarize scores
set_printoptions(precision=3)
print(fit.scores_)
print(fit.get_support())
for i in range(len(fit.get_support())):
  if(fit.get_support()[i]==True):
    print(i," ",df.columns[i+1])
x_trainval = fit.transform(x_trainval)
x_test = fit.transform(x_test)
'''

#LogisticRegression
'''
  selector = SelectFromModel(estimator=LogisticRegression()).fit(x_trainval, y)

  x_trainval = selector.transform(x_trainval)
  x_test = selector.transform(x_test)
  print(x_trainval)
  print(x_test)
'''
#embedded
'''
from sklearn.svm import LinearSVC
from sklearn.datasets import load_iris
from sklearn.feature_selection import SelectFromModel
lsvc = LinearSVC(C=0.01, penalty="l1", dual=False).fit(x_trainval, y)
model = SelectFromModel(lsvc, prefit=True)
x_trainval = model.transform(x_trainval)
x_test = model.transform(x_test)
print(model.get_support())
print(x_trainval)
print(x_test)
'''
#K-neighbors
'''
from sklearn.feature_selection import SequentialFeatureSelector
from sklearn.neighbors import KNeighborsClassifier
from sklearn.datasets import load_iris

knn = KNeighborsClassifier(n_neighbors=20)
sfs = SequentialFeatureSelector(knn, n_features_to_select=20)
sfs.fit(x_trainval, y)
SequentialFeatureSelector(estimator=KNeighborsClassifier(n_neighbors=20),
                          n_features_to_select=20)

print(sfs.get_support())
x_trainval = sfs.transform(x_trainval)
x_test = sfs.transform(x_test)
'''

#tree-based
'''
from sklearn.ensemble import ExtraTreesClassifier
clf = ExtraTreesClassifier(n_estimators=10)
clf = clf.fit(x_trainval, y)
#print(clf.feature_importances_)  
model = SelectFromModel(clf, prefit=True)

x_trainval = model.transform(x_trainval)
x_test = model.transform(x_test)
print(x_trainval.shape)  
print(x_test.shape)  
'''

#RFE
'''
from sklearn.datasets import make_friedman1
from sklearn.feature_selection import RFE
from sklearn.svm import SVR

from sklearn.linear_model import LinearRegression

estimator = LinearRegression()
selector = RFE(estimator, n_features_to_select=8, step=1)
selector = selector.fit(x_trainval, y)
print(selector.support_)
for i in range(len(selector.support_)):
  if(selector.support_[i]==True):
    print(i," ",df.columns[i+1])

print(x_trainval.shape)
x_trainval = selector.transform(x_trainval)
print(x_trainval.shape)
x_test = selector.transform(x_test)
'''



#unchecked
#regression


'''
# pearson's correlation feature selection for numeric input and numeric output
from sklearn.datasets import make_regression
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import f_regression
# define feature selection
fs = SelectKBest(score_func=f_regression, k=10)
# apply feature selection
X_selected = fs.fit_transform(x_trainval, y)
print("Num Features: %d" % fs.n_features_)
print("Selected Features: %s" % fs.support_)
print("Feature Ranking: %s" % fs.ranking_)
'''

'''
# Split data
X_train, X_val, y_train, y_val = train_test_split(x_trainval, y, random_state = 1126, train_size = 0.8)

#upsampling
from imblearn.over_sampling import SMOTE
smt = SMOTE(random_state = 1126)
X_train, y_train = smt.fit_resample(X_train, y_train)
from collections import Counter

'''

#predictions_NB = NB(X_train, X_val, y_train, y_val)
#predictions_KNN = KNN(X_train, X_val, y_train, y_val)
#predictions_RF = RF(X_train, X_val, y_train, y_val, False)
#predictions_SVM = SVM(X_train, X_val, y_train, y_val, True)
'''
predictions_GB = GradientBoosting(X_train, X_val, y_train, y_val, False)

make_pred(predictions_GB, test_id)
'''