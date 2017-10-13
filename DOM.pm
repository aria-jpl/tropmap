# $Id: DOM.pm,v 1.1 2005/04/07 22:11:39 bjn Exp $
# Based on Xerces-p sample 'DOM2hash.pl'
######################################################################
#
# The Apache Software License, Version 1.1
# 
# Copyright (c) 1999-2000 The Apache Software Foundation.  All rights 
# reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer. 
# 
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
# 
# 3. The end-user documentation included with the redistribution,
#    if any, must include the following acknowledgment:  
#       "This product includes software developed by the
#        Apache Software Foundation (http://www.apache.org/)."
#    Alternately, this acknowledgment may appear in the software itself,
#    if and wherever such third-party acknowledgments normally appear.
# 
# 4. The names "Xerces" and "Apache Software Foundation" must
#    not be used to endorse or promote products derived from this
#    software without prior written permission. For written 
#    permission, please contact apache\@apache.org.
# 
# 5. Products derived from this software may not be called "Apache",
#    nor may "Apache" appear in their name, without prior written
#    permission of the Apache Software Foundation.
# 
# THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED.  IN NO EVENT SHALL THE APACHE SOFTWARE FOUNDATION OR
# ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
# ====================================================================
# 
# This software consists of voluntary contributions made by many
# individuals on behalf of the Apache Software Foundation, and was
# originally based on software copyright (c) 1999, International
# Business Machines, Inc., http://www.ibm.com .  For more information
# on the Apache Software Foundation, please see
# <http://www.apache.org/>.
#
######################################################################
############################################################################
# Additional work Copyright 2005, by the California Institute of Technology.
# ALL RIGHTS RESERVED. United States Government Sponsorship acknowledged.
# Any commercial use must be negotiated with the Office of Technology 
# Transfer at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws and regulations.
# By accepting this document, the user agrees to comply with all applicable
# U.S. export laws and regulations.  User has the responsibility to obtain
# export licenses, or other export authority as may be required before
# exporting  such information to foreign countries or providing access to
# foreign persons.
###########################################################################

package DOM2obj;
use strict;
use XML::Xerces qw(error);


package MyNodeFilter;
use strict;
use vars qw(@ISA);
@ISA = qw(XML::Xerces::PerlNodeFilter);
sub acceptNode {
  my ($self, $node) = @_;
  # Accept all nodes
  return $XML::Xerces::DOMNodeFilter::FILTER_ACCEPT;
}


package DOM2obj;

sub new {
    my ($class, %args) = @_;
    my $self = bless {}, ref($class) || $class;

    $self->{_file} = $args{File};

    my $DOM = XML::Xerces::XercesDOMParser->new();
    my $ERROR_HANDLER = XML::Xerces::PerlErrorHandler->new();
    $DOM->setErrorHandler($ERROR_HANDLER);
    eval{$DOM->parse($self->get_file)};
    error($@,"Couldn't parse file: ".$self->get_file)
        if $@;

    my $doc = $DOM->getDocument();
    my $doc_root = $doc->getDocumentElement();
    
    $self->{_root} = $self->_node2obj($doc_root);
    return $self;
}

sub _node2obj {
    my ($self, $doc_node) = @_;
    my $node = DOMnode->new();

    # Set the object properties
    $node->set_node_name($doc_node->getNodeName());
    if ($doc_node->hasAttributes()) {
        my %attrs = $doc_node->getAttributes();
        $node->set_attributes(\%attrs);
    }
    
    # Handle children
    if ($doc_node->hasChildNodes()) {
        my $text;
        foreach my $child ($doc_node->getChildNodes) {
            if ($child->isa('XML::Xerces::DOMElement')) {
                $node->add_child($self->_node2obj($child));
            }
            if ($child->isa('XML::Xerces::DOMText')) {
                $text .= $child->getNodeValue();
            }
        }
        if ($text !~ /^\s*$/) {
            $node->add_text($text);
        }
    }
    return $node;
}

sub get_file {
    my ($self) = @_;
    return $self->{_file};
}

sub get_root {
    my ($self) = @_;
    return $self->{_root};
}

sub find_node {
    # Search for the requested node starting from the root
    # Return a reference to the node if found, or undef if note;
    my ($self, $wanted) = @_;

    my $node = $self->get_root;
    if ($node->get_node_name eq $wanted) {
        return $node;
    }

    foreach my $child ($node->get_children) {
        my $result = $child->find_node($wanted);
        if ($result) {
            return $result;
        }
    }
    return undef;
}

sub print_tree {
    # Print the entire tree
    my ($self, $indent) = @_;

    if (!defined $indent) {
        $indent = '';
    }
    my $node = $self->get_root;
    print $node->get_tree($indent);
}


# $Id: DOM.pm,v 1.1 2005/04/07 22:11:39 bjn Exp $
############################################################################
# Copyright 2005, by the California Institute of Technology.
# ALL RIGHTS RESERVED. United States Government Sponsorship acknowledged.
# Any commercial use must be negotiated with the Office of Technology 
# Transfer at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws and regulations.
# By accepting this document, the user agrees to comply with all applicable
# U.S. export laws and regulations.  User has the responsibility to obtain
# export licenses, or other export authority as may be required before
# exporting  such information to foreign countries or providing access to
# foreign persons.
###########################################################################
#
# This package implements a tree structure that contains a copy of an
# XML:Xerces DOM tree.

package DOMnode;

use strict;

sub new {
    my ($class, %args) = @_;
    my $self = bless {}, ref($class) || $class;

    $self->{_node_name}  = undef;
    $self->{_attributes} = {};
    $self->{_text}       = '';
    $self->{_children}   = [];

    return $self;
}

sub set_node_name {
    my ($self, $node_name) = @_;
    $self->{_node_name} = $node_name;
}

sub get_node_name {
    my ($self) = @_;
    return $self->{_node_name};
}

sub set_attributes {
    my ($self, $attrs) = @_;
    $self->{_attributes} = $attrs;
}

sub get_attributes {
    my ($self) = @_;
    return %{$self->{_attributes}};
}

sub add_child {
    my ($self, $child) = @_;
    push @{$self->{_children}}, $child;
}

sub get_children {
    my ($self) = @_;
    return @{$self->{_children}};
}

sub add_text {
    my ($self, $text) = @_;
    $self->{_text} .= $text;
}

sub get_text {
    my ($self) = @_;
    return $self->{_text};
}

sub get_tree {
    # Print the contents of this node and all child nodes
    my ($self, $indent) = @_;

    if (!defined $indent) {
        $indent = '';
    }
    print $indent, $self->get_node_name;
    print '  ', $self->get_text;
    print "\n";

    my %attr = $self->get_attributes;
    foreach my $key (keys %attr) {
        print $indent, '  ', $key, '  ', $attr{$key}, "\n";
    }
    $indent .= '  ';
    foreach my $child ($self->get_children) {
        print $child->get_tree($indent);
    }
}

sub find_node {
    # Search for the requested node starting here
    # Return a reference to the node if found, or undef if note;
    my ($self, $wanted) = @_;

    if ($self->get_node_name eq $wanted) {
        return $self;
    }

    foreach my $child ($self->get_children) {
        my $result = $child->find_node($wanted);
        if ($result) {
            return $result;
        }
    }
    return undef;
}



1;


1;
