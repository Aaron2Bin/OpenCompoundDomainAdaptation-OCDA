import os
from os.path import join

# Import from torch
import torch
import torch.optim as optim

# Import from Cycada Package 
from ..models.models import get_model
from ..data.data_loader import load_data_multi
from .test_amn_net import test
import pdb

def train_epoch(loader, net, opt_net, epoch):

    log_interval = 10 # specifies how often to display

    net.train()

    for batch_idx, (data, target) in enumerate(loader):

        # make data variables
        if torch.cuda.is_available():
            data = data.cuda()
            target = target.cuda()

        data.require_grad = False
        target.require_grad = False
        
        # zero out gradients
        opt_net.zero_grad()
       
        # forward pass
        score = net(data)
        loss = net.criterion_cls(score, target)
        
        # backward pass
        loss.backward()
        
        # optimize classifier and representation
        opt_net.step()
       
        # Logging
        if batch_idx % log_interval == 0:
            print('[Train] Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(loader.dataset),
                100. * batch_idx / len(loader), loss.item()), end="")
            _, pred = torch.max(score, 1)
            correct = (pred == target).cpu().sum().item()
            acc = correct / len(pred) * 100.0
            print('  Acc: {:.2f}'.format(acc))


def train(data, datadir, model, num_cls, outdir='', 
        num_epoch=100, batch=128, 
        lr=1e-4, betas=(0.9, 0.999), weight_decay=0):
    """Train a classification net and evaluate on test set."""

    # Setup GPU Usage
    if torch.cuda.is_available(): 
        kwargs = {'num_workers': 1, 'pin_memory': True}
    else:
        kwargs = {}

    ############
    # Load Net #
    ############
    net = get_model(model, num_cls=num_cls)
    print('-------Training net--------')
    print(net)

    ############################
    # Load train and test data # 
    ############################
    train_data = load_data_multi(data, 'train', batch=batch, 
        rootdir=datadir, num_channels=net.num_channels, 
        image_size=net.image_size, download=True, kwargs=kwargs)
    
    test_data = load_data_multi(data, 'test', batch=batch, 
        rootdir=datadir, num_channels=net.num_channels, 
        image_size=net.image_size, download=True, kwargs=kwargs)
   
    ###################
    # Setup Optimizer #
    ###################
    opt_net = optim.Adam(net.parameters(), lr=lr, betas=betas, 
            weight_decay=weight_decay)
    
    #########
    # Train #
    #########
    print('Training {} model for {}'.format(model, data))
    for epoch in range(num_epoch):
        train_epoch(train_data, net, opt_net, epoch)
    
    ########
    # Test #
    ########
    if test_data is not None:
        print('Evaluating {}-{} model on {} test set'.format(model, data, data))
        test(test_data, net)

    ############
    # Save net #
    ############
    os.makedirs(outdir, exist_ok=True)
    outfile = join(outdir, '{:s}_net_{:s}.pth'.format(model, data))
    print('Saving to', outfile)
    net.save(outfile)

    return net
