import tensorflow as tf
import numpy as np
from scipy.ndimage.filters import gaussian_filter1d

def compute_saliency_maps(X, y, model):
    """
    Compute a class saliency map using the model for images X and labels y.

    Input:
    - X: Input images, numpy array of shape (N, H, W, 3)
    - y: Labels for X, numpy of shape (N,)
    - model: A SqueezeNet model that will be used to compute the saliency map.

    Returns:
    - saliency: A numpy array of shape (N, H, W) giving the saliency maps for the
    input images.
    """
    saliency = None
    # Compute the score of the correct class for each example.
    # This gives a Tensor with shape [N], the number of examples.
    #
    # Note: this is equivalent to scores[np.arange(N), y] we used in NumPy
    # for computing vectorized losses.

    ###############################################################################
    # TODO: Produce the saliency maps over a batch of images.                     #
    #                                                                             #
    # 1) Define a gradient tape object and watch input Image variable             #
    # 2) Compute the “loss” for the batch of given input images.                  #
    #    - get scores output by the model for the given batch of input images     #
    #    - use tf.gather_nd or tf.gather to get correct scores                    #
    # 3) Use the gradient() method of the gradient tape object to compute the     #
    #    gradient of the loss with respect to the image                           #
    # 4) Finally, process the returned gradient to compute the saliency map.      #
    ###############################################################################
    # *****START OF YOUR CODE (DO NOT DELETE/MODIFY THIS LINE)*****

    # numpy array to tf tensor
    tensor_x = tf.convert_to_tensor(X)
    # forward pass minibatch and pick scores for correct classes
    with tf.GradientTape() as tape:
        tape.watch(tensor_x)
        scores = tf.gather_nd(model(tensor_x), tf.stack((tf.range(X.shape[0]), y), axis=1))
    # backprop to find the derivative of the scores
    grads = tape.gradient(scores, tensor_x)
    # extract max of absolute value of the grad
    saliency = tf.math.maximum(tf.math.abs(grads),-1)

    # *****END OF YOUR CODE (DO NOT DELETE/MODIFY THIS LINE)*****
    ##############################################################################
    #                             END OF YOUR CODE                               #
    ##############################################################################
    return saliency

def make_fooling_image(X, target_y, model):
    """
    Generate a fooling image that is close to X, but that the model classifies
    as target_y.

    Inputs:
    - X: Input image, a numpy array of shape (1, 224, 224, 3)
    - target_y: An integer in the range [0, 1000)
    - model: Pretrained SqueezeNet model

    Returns:
    - X_fooling: An image that is close to X, but that is classifed as target_y
    by the model.
    """

    # Make a copy of the input that we will modify
    X_fooling = X.copy()

    # Step size for the update
    learning_rate = 1

    ##############################################################################
    # TODO: Generate a fooling image X_fooling that the model will classify as   #
    # the class target_y. Use gradient *ascent* on the target class score, using #
    # the model.scores Tensor to get the class scores for the model.image.   #
    # When computing an update step, first normalize the gradient:               #
    #   dX = learning_rate * g / ||g||_2                                         #
    #                                                                            #
    # You should write a training loop, where in each iteration, you make an     #
    # update to the input image X_fooling (don't modify X). The loop should      #
    # stop when the predicted class for the input is the same as target_y.       #
    #                                                                            #
    # HINT: Use tf.GradientTape() to keep track of your gradients and            #
    # use tape.gradient to get the actual gradient with respect to X_fooling.    #
    #                                                                            #
    # HINT 2: For most examples, you should be able to generate a fooling image  #
    # in fewer than 100 iterations of gradient ascent. You can print your        #
    # progress over iterations to check your algorithm.                          #
    ##############################################################################
    # *****START OF YOUR CODE (DO NOT DELETE/MODIFY THIS LINE)*****
    
    # numpy array to tf tensor
    X_fooling = tf.convert_to_tensor(X_fooling)

    # cap iterations
    for i in range(100):
        # forward pass and prediction
        with tf.GradientTape() as tape:
            tape.watch(X_fooling)
            scores = model(X_fooling)
            true_score = scores[:,target_y]
        # break when successful
        pred = tf.math.argmax(scores,1)
        if pred == target_y:
            break
        else:
            # backprop
            grads = tape.gradient(true_score, X_fooling)
            dX = learning_rate * grads / tf.norm(grads)
            X_fooling += dX

    # *****END OF YOUR CODE (DO NOT DELETE/MODIFY THIS LINE)*****
    ##############################################################################
    #                             END OF YOUR CODE                               #
    ##############################################################################
    return X_fooling

def class_visualization_update_step(X, model, target_y, l2_reg, learning_rate):
    ########################################################################
    # TODO: Compute the value of the gradient of the score for             #
    # class target_y with respect to the pixels of the image, and make a   #
    # gradient step on the image using the learning rate. You should use   #
    # the tf.GradientTape() and tape.gradient to compute gradients.        #
    #                                                                      #
    # Be very careful about the signs of elements in your code.            #
    ########################################################################
    # *****START OF YOUR CODE (DO NOT DELETE/MODIFY THIS LINE)*****

    # numpy array to tf tensor
    tensor_x = tf.convert_to_tensor(X)
    # forward pass and objective function
    with tf.GradientTape() as tape:
        tape.watch(tensor_x)
        scores = model(tensor_x)
        objective = scores[:,target_y] - (l2_reg * tf.norm(tensor_x))
    # backprop on the image
    grads = tape.gradient(objective, tensor_x)
    dX = learning_rate * grads
    X += dX

    # X = tf.convert_to_tensor(X)
    # with tf.GradientTape() as tape:
    #     tape.watch(X)
    #     scores = model(X)
    #     target_scores = scores[:,target_y]
    #     loss = target_scores - l2_reg * np.sum(X * X)
    # dx = tape.gradient(loss, X)
    # X += learning_rate * dx

    # *****END OF YOUR CODE (DO NOT DELETE/MODIFY THIS LINE)*****
    ############################################################################
    #                             END OF YOUR CODE                             #
    ############################################################################

    return X

def blur_image(X, sigma=1):
    X = gaussian_filter1d(X, sigma, axis=1)
    X = gaussian_filter1d(X, sigma, axis=2)
    return X

def jitter(X, ox, oy):
    """
    Helper function to randomly jitter an image.

    Inputs
    - X: Tensor of shape (N, H, W, C)
    - ox, oy: Integers giving number of pixels to jitter along W and H axes

    Returns: A new Tensor of shape (N, H, W, C)
    """
    if ox != 0:
        left = X[:, :, :-ox]
        right = X[:, :, -ox:]
        X = tf.concat([right, left], axis=2)
    if oy != 0:
        top = X[:, :-oy]
        bottom = X[:, -oy:]
        X = tf.concat([bottom, top], axis=1)
    return X
