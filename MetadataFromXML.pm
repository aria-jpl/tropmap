#! /usr/bin/perl
# $Id: MetadataFromXML.pm,v 1.16 2007/06/20 22:34:04 ratcliff Exp $
##############################################################################
# This file is based on:
# Filename    : aprioriXyzFromProcInputXml.pl
# Date        : 03/2005
# Authors     : Paul Jamason
# Purpose     : print site, xyz, xyz sigmas using model terms in 
#               procMetadataInput.xml file
# Mods        : Minimal modifications for JPL SCIGN analysis by Brian Newport
##############################################################################

package MetadataFromXML;

use strict;
use Carp qw(&cluck &croak &confess);
use File::Basename;
use XML::Xerces;

use RefinedSeriesModel qw(GetCoordsFromModelTerms);
use ConvertDate;
use DOM;


my %IGNORED_ELEMENTS = (
                        'geod:referencePoint'           => 1,

                        'geod:manufacturerSerialNumber' => 1,

                        'geod:gnssReceiverConfig'     => 1,
                        'geod:siteProcAntDome'        => 1,
                        'geod:xSigma'                 => 1,
                        'geod:ySigma'                 => 1,
                        'geod:zSigma'                 => 1,

                        'geod:xSigma'                  => 1,
                        'geod:ySigma'                  => 1,
                        'geod:zSigma'                  => 1,

                        'geod:gnssReceiverConfig'      => 1,
                        'geod:siteProcAntDome'         => 1,
                        );


sub new {
    my ($class, @args) = @_;
    my $self = bless({}, ref $class || $class);

    my ($xmlFile, $verbose) = @args;

    if ($xmlFile =~ /^ftp:/ || $xmlFile =~ /^http:/) {
        $xmlFile = $self->_download($xmlFile);
    }
    my $obj = DOM2obj->new('File' => $xmlFile);
    my $pmi = $obj->find_node('procMetadataInput');
    if (! $pmi) {
        die "ERROR: procMetadataInput not found in $xmlFile\n";
    }
    my ($md_date, $md) = $self->do_procMetadataInput($pmi);

    $self->{_creation_date} = $md_date;
    $self->{_md_antennas}   = $md->{'Antennas'};
    $self->{_md_sites}      = $md->{'Sites'};
    $self->{_verbose}       = $verbose;

    return $self;
}

#---------------------------- Private Methods ---------------------------------
sub _download {
    my ($self, $url) = @_;

    my ($name, $path) = fileparse($url, '');

    if (-e $name) {
        my $status = system "mv -f $name $name.1";
        if ($status) {
            confess "mv -f $name $name.1 FAILED";
        }
    }
    if (-e "wget.log") {
        my $status = system "mv -f wget.log wget.log.1";
        if ($status) {
            confess "mv -f wget.log wget.log.1 FAILED";
        }
    }

    # The wget -N option causes an existing file to be overwritten
    # if a newer copy is available on the server
    my $status = system "wget --passive-ftp -N -o wget.log $url";
    if ($status) {
        confess "wget failed";
    }
    return $name;
}

sub _unhandled_node {
    my ($self, $node, $name) = @_;
    
    if ($IGNORED_ELEMENTS{$name}){
        if ($self->{_verbose}) {
            print "Skipping ignored element $name\n";
        }
        return;
    }
    print "Unhandled in ", $node->get_node_name, ":  $name\n";
    my ($package, $filename, $line) = caller;
    print "at $filename line $line\n\n";
}

#---------------------------- Public Methods ----------------------------------
sub get_all_antennas {
    my ($self) = @_;
    return sort keys %{$self->{_md_antennas}};
}

sub get_all_sites {
    my ($self) = @_;
    return sort keys %{$self->{_md_sites}};
}

sub get_nominal_xyz {
    # Return (x, y, z) if successful, otherwise return an error string
    my ($self, $site, $year, $doy) = @_;

    if ($self->{_verbose}) {
        print "------------------------------------------------------------\n";
        print "$site Getting nominal XYZ\n";
    }

    # Get the aprioriXYZ
    my $ref = $self->{_md_sites}->{$site}->{apriori_xyz};

    my $aprX = $ref->{x};
    my $aprY = $ref->{y};
    my $aprZ = $ref->{z};

    # Get the refXYZ (used by precise model)
    my $r_mmt = $self->{_md_sites}->{$site}->{'neu'};

    my $refX = $r_mmt->{'ref_xyz'}{x};
    my $refY = $r_mmt->{'ref_xyz'}{y};
    my $refZ = $r_mmt->{'ref_xyz'}{z};

    if (!defined $refX or !defined $refY or !defined $refZ) {
        if ($self->{_verbose}) {
            print "$site Missing refXYZ, using aprioriXYZ (Scout) instead\n";
        }
        # Use aprioriXYZ instead
        if (!defined $aprX or !defined $aprY or !defined $aprZ) {
            if ($self->{_verbose}) {
                print "$site Also missing aprioriXYZ\n";
            }
            return ('Missing refXYZ and aprioriXYZ');
        }
        return $aprX, $aprY, $aprZ;
    }

    # Report if refXYZ = aprioriXYZ
    if ($self->{_verbose}) {
        if ($refX == $aprX && $refY == $aprY && $refZ == $aprZ) {
            print "$site refXYZ equals apriorXYZ\n";
        }
    }

    # hash of component terms
    foreach my $key2 (qw(n e u)) {
        if ($self->{_verbose}) {
            print "$site $key2\n";
        }
        my $r_comp = $r_mmt->{$key2};

        # hash of "slope", "offset", "decay" and "various" hashes
        for my $key3 (keys %$r_comp) {
            my $r_various = $r_comp->{'various'};
            my $r_slopes = $r_comp->{'slopes'};
            my $r_decays = $r_comp->{'decays'};
            my $r_offsets = $r_comp->{'offsets'};
            my $r_slopeDiffs = $r_comp->{'slopeDiffs'};
            
            if ($self->{_verbose}){
                if ($key3 eq "slopes"){
                    print "slopes\n";
                    for my $refEpoch (sort keys %$r_slopes){
                        print "$refEpoch $r_slopes->{$refEpoch}{slope}\n";
                    }
                }
                if ($key3 eq "offsets"){
                    print "offsets\n";
                    for my $refEpoch (sort keys %$r_offsets){
                        print "$refEpoch $r_offsets->{$refEpoch}{offset} $r_offsets->{$refEpoch}{coseismic}\n";
                    }
                }
                if ($key3 eq "decays"){
                    print "decays\n";
			for my $refEpoch(sort keys %$r_decays){
			    print "$refEpoch $r_decays->{$refEpoch}{decay} $r_decays->{$refEpoch}{tau}\n";
			}
                }
                if ($key3 eq "slopeDiffs"){
                    print "slopeDiffs\n";
                    for my $refEpoch (sort keys %$r_slopeDiffs){
                        print "$refEpoch $r_slopeDiffs->{$refEpoch}{diff}\n";
                    }
                }
                if ($key3 eq "various"){
                    print "various\n";
                    for my $key4 (sort keys %$r_various){
                        print "$key4 $r_various->{$key4}\n";
                    }
                }
                # end verbose conditional
            }
        }
    }
    
    my ($x, $y, $z) = &PROC::RefinedSeriesModel::GetCoordsFromModelTerms($year, $doy, $r_mmt, $refX, $refY, $refZ, $self->{_verbose});

    return $x, $y, $z;
}

sub get_creation_date {
    my ($self) = @_;
    return $self->{_creation_date};
}

sub get_site_equipment {
    # Return refererence to equipment hash or undef if site not active
    my ($self, $site, $iso_date) = @_;

    my $found_epoch;
    my $requip = $self->{_md_sites}->{$site}->{'Equipment'};

    foreach my $start_epoch (sort keys %$requip) {
        next if $iso_date lt $start_epoch;
        my $end_epoch = $requip->{$start_epoch}->{'end_epoch'};
        next if defined $end_epoch && $iso_date gt $end_epoch;
        $found_epoch = $start_epoch;
        last;
    }
    if ($found_epoch) {
        return $requip->{$found_epoch};
    }
    else {
        return undef;
    }
}

sub get_antenna_info {
    # Return reference to hash
    my ($self, $antenna_type) = @_;
    return $self->{_md_antennas}->{$antenna_type};
}


#---------------------------- XML Code ---------------------------------------
sub do_procMetadataInput {
    my ($self, $node) = @_;
 
    my $md = {};
    my $md_date;
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        if ($name eq 'creationDate') {
            $md_date = $child->get_text;
            next;
        }
        if ($name eq 'siteProcMetadata') {
            my ($key, $href) = $self->do_siteProcMetadata($child);
            $md->{$key} = $href;
            next;
        }
        if ($name eq 'antPhaseCenterCatalog') {
            my ($key, $href) = $self->do_antPhaseCenterCatalog($child);
            $md->{$key} = $href;
            next;
        }
        $self->_unhandled_node($node, $name);
    }
    return ($md_date, $md);
}

sub do_siteProcMetadata {
    my ($self, $node) = @_;
 
    my $dref = {};
    foreach my $child ($node->get_children) {
        my ($ns, $name) = split ':', $child->get_node_name;
        if ($name eq 'indivSiteProcMetadata') {
            my ($site, $href) = $self->do_indivSiteProcMetadata($child);
            $dref->{$site} = $href;
            next;
        }
        $self->_unhandled_node($node, $child->get_node_name);
    }
    return ('Sites', $dref);
}
 
sub do_indivSiteProcMetadata {
    my ($self, $node) = @_;
 
    my $site;
    my $dref = {};
    my $requip = {};
    $dref->{'Equipment'} = $requip;
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $name =~ s/^\w+://;
        if ($name eq 'fourCharacterID') {
            $site = $child->get_text;
            next;
        }
        if ($name eq 'equipmentMetadataEntry') {
            my ($start_epoch, $href) = $self->do_equipmentMetadataEntry($child);
            $requip->{$start_epoch} = $href;
            next;
        }
        if ($name eq 'aprioriXYZ') {
            my ($key, $href) = $self->do_aprioriXYZ($child);
            $dref->{$key} = $href;
            next;
        }
        if ($name eq 'neuMotionModelTerms') {
            my ($key, $href) = $self->do_neuMotionModelTerms($child);
            $dref->{$key} = $href;
            next;
        }
        $self->_unhandled_node($node, $child->get_node_name);
    }
    return ($site, $dref);
}


sub do_aprioriXYZ {
    my ($self, $node) = @_;
 
    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $name =~ s/^\w+://;
        if ($name eq 'x') {
	    $dref->{x} = $child->get_text;
	    next;
	}

        if ($name eq 'y') {
	    $dref->{y} = $child->get_text;
	    next;
	}

        if ($name eq 'z') {
	    $dref->{z} = $child->get_text;
	    next;
	}

        $self->_unhandled_node($node, $child->get_node_name);
    }
    return ('apriori_xyz', $dref);
}


sub do_neuMotionModelTerms {
    my ($self, $node) = @_;
 
    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $name =~ s/^\w+://;
        if ($name eq 'componentTerms') {
	    my ($component,$href) = $self->do_component_terms($child);
	    $dref->{$component}= $href;
	    next;
	}

	# we know this appears after component terms.  need to append
	# this to hash
        if ($name eq 'refXYZ'){
	    my ($key,$href) = $self->do_ref_xyz($child);
	    $dref->{$key}= $href;
	    next;
	}

        $self->_unhandled_node($node, $child->get_node_name);
    }
    return ('neu', $dref);
}


sub do_component_terms {
    my ($self, $node) = @_;
 
    my $component;
    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $name =~ s/^\w+://;
        if ($name eq 'component') {
	    $component = $child->get_text;
	    next;
	}
	# model wants parameters in mm
        if ($name eq 'slope') {
	    my ($startEpoch,$href) = $self->do_slope($child);
	    $dref->{slopes}{$startEpoch}= $href;
	    next;
	}
        if ($name eq 'offset') {
	    my ($startEpoch,$href) = $self->do_offset($child);
	    $dref->{offsets}{$startEpoch}= $href;
	    next;
	}
        if ($name eq 'postSeismicDecay') {
	    my ($startEpoch,$href) = $self->do_decay($child);
	    $dref->{decays}{$startEpoch}= $href;
	    next;
	}
        if ($name eq 'velocityChange') {
	    my ($startEpoch,$href) = $self->do_vel_change($child);
	    $dref->{slopeDiffs}{$startEpoch}= $href;
	    next;
	}
        if ($name eq 'yInt') {
            $dref->{various}{y_int} = $child->get_text;
	    next;
	}
        if ($name eq 'postfitRms'){
            $dref->{various}{postfit_rms} = $child->get_text;
	    next;
	}
        if ($name eq 'sinAnn') {
	    $dref->{various}{sin_ann} = $self->do_semi_ann_term($child);
	    next;
	}
        if ($name eq 'cosAnn') {
	    $dref->{various}{cos_ann} = $self->do_semi_ann_term($child);
	    next;
	}
        if ($name eq 'sinSemiAnn') {
	    $dref->{various}{sin_semi_ann} = $self->do_semi_ann_term($child);
	    next;
	}
        if ($name eq 'cosSemiAnn') {
	    $dref->{various}{cos_semi_ann} = $self->do_semi_ann_term($child);
	    next;
	}
        if ($name eq 'annual') {
	    next;
	}
        if ($name eq 'semiAnn') {
	    next;
	}
        if ($name eq 'yIntSigma') {
	    next;
	}
        $self->_unhandled_node($node, $child->get_node_name);
    }

    if ($component eq "north"){
        $component = "n";
    }
    elsif ($component eq "east"){
        $component = "e";
    }
    elsif ($component eq "up"){
        $component = "u";
    }
    return ($component, $dref);
}
 

sub do_ref_xyz {
    my ($self, $node) = @_;
 
    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $name =~ s/^\w+://;
        if ($name eq 'x') {
	    $dref->{x} = $child->get_text;
	    next;
	}
        if ($name eq 'y') {
	    $dref->{y} = $child->get_text;
	    next;
	}
        if ($name eq 'z') {
	    $dref->{z} = $child->get_text;
	    next;
	}
        $self->_unhandled_node($node, $child->get_node_name);
    }
    return ('ref_xyz', $dref);
}


sub do_slope {
    my ($self, $node) = @_;
 
    my $startEpoch;
    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $name =~ s/^\w+://;
        if ($name eq 'startRefEpoch') {
	    $startEpoch = $child->get_text;
	    $startEpoch = $self->localConvertDate($startEpoch);
	    next;
	}
        if ($name eq 'stopRefEpoch') {
	    next;
	}
        if ($name eq 'sigma') {
	    next;
	}
        if ($name eq 'magnitude'){
	    $dref->{slope}= $child->get_text;
	    next;
	}
        $self->_unhandled_node($node, $child->get_node_name);
    }
    return ($startEpoch, $dref);
}


sub do_offset {
    my ($self, $node) = @_;
 
    my $startEpoch;
    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $name =~ s/^\w+://;
        if ($name eq 'referenceEpoch') {
	    $startEpoch = $child->get_text;
	    $startEpoch = $self->localConvertDate($startEpoch);
	    next;
	}
        if ($name eq 'magnitude'){
	    $dref->{offset}= $child->get_text;
	    next;
	}
        if ($name eq 'coseismic'){
	    $dref->{coseismic}= $child->get_text;
	    next;
	}
        if ($name eq 'sigma') {
	    next;
	}
        $self->_unhandled_node($node, $child->get_node_name);
    }
    return ($startEpoch, $dref);
}


sub do_vel_change{
    my ($self, $node) = @_;
 
    my $startEpoch;
    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $name =~ s/^\w+://;
        if ($name eq 'referenceEpoch') {
	    $startEpoch = $child->get_text;
	    $startEpoch = $self->localConvertDate($startEpoch);
	    next;
	}
        if ($name eq 'magnitude'){
	    $dref->{diff}= $child->get_text;
	    next;
	}
        if ($name eq 'sigma') {
	    next;
	}
        $self->_unhandled_node($node, $child->get_node_name);
    }
    return ($startEpoch, $dref);
}


sub do_decay {
    my ($self, $node) = @_;
 
    my $startEpoch;
    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $name =~ s/^\w+://;
        if ($name eq 'referenceEpoch') {
	    $startEpoch = $child->get_text;
	    $startEpoch = $self->localConvertDate($startEpoch);
	    next;
	}
        if ($name eq 'magnitude'){
	    $dref->{decay} = $child->get_text;
	    next;
	}
        if ($name eq 'tau'){
	    $dref->{tau} = $child->get_text;

	    # strip non-numeric characters (e.g., P280D to 280)
	    $dref->{tau} =~ s/\D//g;
	    next;
	}
        if ($name eq 'sigma') {
	    next;
	}
        $self->_unhandled_node($node, $child->get_node_name);
    }
    return ($startEpoch, $dref);
}


sub do_semi_ann_term {
    my ($self, $node) = @_;
 
    my $magnitude;
    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $name =~ s/^\w+://;
        if ($name eq 'magnitude'){
	    $magnitude= $child->get_text;
	    next;
	}
        if ($name eq 'sigma') {
	    next;
	}

        if ($name eq 'phase') {
	    next;
	}
        $self->_unhandled_node($node, $child->get_node_name);
    }
    return ($magnitude);
}

#-------------------------- Site Equipment ------------------------------------
sub do_equipmentMetadataEntry {
    my ($self, $node) = @_;

    my $start_epoch;
    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $name =~ s/^\w+://;
        if ($name eq 'dateInstalled') {
            $start_epoch = $child->get_text;
            next;
        }
        if ($name eq 'dateRemoved') {
            $dref->{end_epoch} = $child->get_text;
            next;
        }
        if ($name eq 'siteProcReceiver') {
            $dref->{receiver_type} = $self->do_siteProcReceiver($child);
            next;
        }
        if ($name eq 'siteProcAntenna') {
            $dref->{antenna_type} = $self->do_siteProcAntenna($child);
            next;
        }
        if ($name eq 'antennaHeightInfo') {
            $dref->{antenna_height} = $self->do_antennaHeightInfo($child);
            next;
        }
        if ($name eq 'marker-arpNorthEcc.') {
            $dref->{north_eccentricity} = $child->get_text;
            next;
        }
        if ($name eq 'marker-arpEastEcc.') {
            $dref->{east_eccentricity} = $child->get_text;
            next;
        }
        $self->_unhandled_node($node, $child->get_node_name);
    }
    return ($start_epoch, $dref);
}

sub do_siteProcReceiver {
    my ($self, $node) = @_;

    my $receiver_type;
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        if ($name eq 'geod:igsModelCode') {
            $receiver_type = $child->get_text;
            next;
        }
        $self->_unhandled_node($node, $name);
    }
    return $receiver_type;
}

sub do_siteProcAntenna {
    my ($self, $node) = @_;

    my $antenna_type;
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        if ($name eq 'geod:igsModelCode') {
            $antenna_type = $child->get_text;
            next;
        }
        $self->_unhandled_node($node, $name);
    }
    return $antenna_type;
}

sub do_antennaHeightInfo {
    my ($self, $node) = @_;

    my $antenna_height;
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        if ($name eq 'geod:value') {
            $antenna_height = $child->get_text;
            next;
        }
        if ($name eq 'geod:type') {
            if ($child->get_text ne 'vertical') {
                die "ERROR: geod:antennaHeightInfo geod:type is not 'vertical'\n";
            }
            next;
        }
        $self->_unhandled_node($node, $name);
    }
    return $antenna_height;
}

#--------------------------- Antenna Phase Centers ----------------------------
sub do_antPhaseCenterCatalog {
    my ($self, $node) = @_;

    my $ant_type;
    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        if ($name eq 'antPhaseCenter') {
            my ($key, $href) = $self->do_antPhaseCenter($child);
            $dref->{$key} = $href;
            next;
        }
        $self->_unhandled_node($node, $name);
    }
    return ('Antennas', $dref);
}

sub do_antPhaseCenter {
    my ($self, $node) = @_;

    my $ant_type;
    my $dref;
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        if ($name eq 'geod:igsModelCode') {
            $ant_type = $child->get_text;
            next;
        }
        if ($name eq 'geod:nominalPhaseCenterGeometry') {
            $dref = $self->do_ga_nominalPhaseCenterGeometry($child);
            next;
        }
        $self->_unhandled_node($node, $name);
    }
    return $ant_type, $dref;
}

sub do_ga_nominalPhaseCenterGeometry {
    my ($self, $node) = @_;

    my $dref = {};
    foreach my $child ($node->get_children) {
        my $name = $child->get_node_name;
        $dref->{$name} = $child->get_text;
    }
    return $dref;
}

#------------------------------ Utilities ------------------------------------
sub localConvertDate {
    my ($self, $startEpoch) = @_;
    
    my ($year,$doy) = &ConvertDate::xsddate2ydoy($startEpoch);
    $startEpoch = join("",$year,$doy);
    return($startEpoch);
}

1;
