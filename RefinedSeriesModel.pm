# PROC::RefinedSeriesModel.pm              -*- Perl -*-
#
# This is the PROC::RefinedSeriesModel library.
# It contains routines used to retrieve refined series model parameters
# and calculate coordinates from this model.

package PROC::RefinedSeriesModel;

use ConvertDate;

##############################################################
# GetModeledCoords: return hash of refined model xyz and wgs #  
# coordinates for specified epoch                            #
#                                                            #
# arguments: site id, filter type, year, day-of-year,        #
# coordinate source id, db handle                            #
##############################################################

sub GetModeledCoords {

    use strict;

    my ($start) = (times)[0];

    my ($siteID,$type,$year,$doy,$coordSourceID,$dbh,$verbose) = @_;

    # get site id, type (flt/unf), ref year, ref day
    # will return hash or array of neu or xyz
    my (%coordInfo,%modelInfo);

    # convert year, day to decyr
    $doy = SOPAC::Utils::formatDay($doy);

    my ($refEpoch) = ConvertDate::ydoy2decyr($year,$doy);

    ################################
    # connect to db for below code #
    ################################

    ############
    # neu loop #
    ############

    my ($refX,$refY,$refZ,%postfitRms);
    my (@comps) = ("n", "e", "u");
    for my $comp (@comps) {


	my ($localStart) = (times)[0];
        ###########################################
        # get site vel id for this site/comp/type #
        ###########################################
	
	
	my ($siteVelID) = &PROC::GeneralDB::getSiteVelID($siteID,$comp,$type,$coordSourceID,$dbh);	
	if ($verbose){print STDERR "aa1 $siteVelID $siteID $comp $type $coordSourceID\n"};
	
	

	# no site vel id for site/type: exit
	if (!($siteVelID)) {
	    return(undef);
	}

	my ($yInt,$yIntSig,$sinAnn,$cosAnn,$sinSemiAnn,$cosSemiAnn,
	    $startEpoch,$endEpoch,$postfitRms);
	my ($dbYInt,$dbYIntSig,$dbSinAnn,$dbCosAnn,$dbSinSemiAnn,$dbCosSemiAnn,
	    $dbSinAnnSig,$dbCosAnnSig,$dbSinSemiAnnSig,$dbCosSemiAnnSig,
	    $dbStartEpoch,$dbEndEpoch,$dbRefX,$dbRefY,$dbRefZ,$dbPostfitRms);
	my ($dbMsSlope,$dbMsSlopeSig,$dbMsStartEpoch,$dbMsEndEpoch,
	    $dbMsdDiff,$dbMsdDiffSig,$dbMsdStartEpoch,
	    $dbMoOffset,$dbMoOffsetSig,$dbMoCoseismic,$dbMoStartEpoch,
	    $dbMdDecay,$dbMdDecaySig,$dbMdTau,$dbMdStartEpoch);


	####################################################
	# get single value per site/comp/type model values #
	####################################################

	my $tables = "site_velocities sv, modeled_slopes ms, ";
        $tables .= "modeled_slope_diffs msd, modeled_decays md, ";
	$tables .= "modeled_offsets mo";

	my $fields  = "sv.y_int,sv.y_int_sig,";
	$fields .= "sv.sin_ann,sv.cos_ann,sv.sin_semi_ann,sv.cos_semi_ann,";
	$fields .= "sv.sin_ann_sig,sv.cos_ann_sig,";
	$fields .= "sv.sin_semi_ann_sig,sv.cos_semi_ann_sig,";
	$fields .= "sv.ref_x,sv.ref_y,sv.ref_z,sv.postfit_rms,";
	$fields .= "to_char(sv.start_ref_epoch,\'YYYYDDD\'),";
	$fields .= "to_char(sv.end_ref_epoch,\'YYYYDDD\'),";

	$fields .= "ms.magnitude,ms.magnitude_sig,";
	$fields .= "to_char(ms.start_ref_epoch,\'YYYYDDD\'),";
	$fields .= "to_char(ms.end_ref_epoch,\'YYYYDDD\'),";

	$fields .= "msd.magnitude,msd.magnitude_sig,";
	$fields .= "to_char(msd.ref_epoch,\'YYYYDDD\'),";

	$fields .= "mo.magnitude,mo.magnitude_sig,mo.coseismic,";
	$fields .= "to_char(mo.ref_epoch,\'YYYYDDD\'),";

	$fields .= "md.magnitude,md.magnitude_sig,md.tau,";
	$fields .= "to_char(md.ref_epoch,\'YYYYDDD\')";

	my $restrictions = "sv.site_vel_id = ? and ";
	$restrictions .= "sv.site_vel_id = ms.site_vel_id (+) and ";
	$restrictions .= "sv.site_vel_id = msd.site_vel_id (+) and ";
	$restrictions .= "sv.site_vel_id = mo.site_vel_id (+) and ";
	$restrictions .= "sv.site_vel_id = md.site_vel_id (+)";


	my $sql = "select $fields from $tables where $restrictions";
	
	my $sth = $dbh->prepare($sql);
	
	$sth->execute($siteVelID);
	
	$sth->bind_columns(undef, \$dbYInt,\$dbYIntSig,\$dbSinAnn,\$dbCosAnn,
			   \$dbSinSemiAnn,\$dbCosSemiAnn,
			   \$dbSinAnnSig,\$dbCosAnnSig,
			   \$dbSinSemiAnnSig,\$dbCosSemiAnnSig,
			   \$dbRefX,\$dbRefY,\$dbRefZ,\$dbPostfitRms,
			   \$dbStartEpoch,\$dbEndEpoch,
			   \$dbMsSlope,\$dbMsSlopeSig,\$dbMsStartEpoch,
			   \$dbMsEndEpoch,
			   \$dbMsdDiff,\$dbMsdDiffSig,
			   \$dbMsdStartEpoch,
			   \$dbMoOffset,\$dbMoOffsetSig,\$dbMoCoseismic,
			   \$dbMoStartEpoch,
			   \$dbMdDecay,\$dbMdDecaySig,\$dbMdTau,
			   \$dbMdStartEpoch);
	
	if ($verbose){print STDERR "rsm: $sql $siteVelID\n"};	
	
	while($sth->fetch) {
	    $modelInfo{$comp}{various} = {
		y_int => $dbYInt,
		y_int_sig => $dbYIntSig,
		sin_ann => $dbSinAnn,
		cos_ann => $dbCosAnn,
		sin_semi_ann => $dbSinSemiAnn,
		cos_semi_ann => $dbCosSemiAnn,
		sin_ann_sig => $dbSinAnnSig,
		cos_ann_sig => $dbCosAnnSig,
		sin_semi_ann_sig => $dbSinSemiAnnSig,
		cos_semi_ann_sig => $dbCosSemiAnnSig,
		ref_x => $dbRefX,
		ref_y => $dbRefY,
		ref_z => $dbRefZ,
		start_epoch => $dbStartEpoch,
		end_epoch => $dbEndEpoch,
		postfit_rms => $dbPostfitRms,
	    };
	    

	    # calculate annual, semi-annual terms.  these are not used here
	    # but may be needed by external apps
	
	    $modelInfo{$comp}{various}{annual} =  sqrt($dbSinAnn**2 + $dbCosAnn**2);

	    $modelInfo{$comp}{various}{ann_sig} = sqrt($dbSinAnnSig**2 + $dbCosAnnSig**2);	

	    $modelInfo{$comp}{various}{ann_phase} = -(atan2(-$dbSinAnn,$dbCosAnn));

	    if ($modelInfo{$comp}{various}{ann_phase} < 0.) {
		my ($pi) = atan2(1,1)*4;
		$modelInfo{$comp}{various}{ann_phase}=$modelInfo{$comp}{various}{ann_phase}+2*$pi;
	    }
	
	    $modelInfo{$comp}{various}{semi_ann} =  sqrt($dbSinSemiAnn**2 + $dbCosSemiAnn**2);	    
	    $modelInfo{$comp}{various}{semi_ann_sig} =  sqrt($dbSinSemiAnnSig**2 + $dbCosSemiAnnSig**2);	
	    $modelInfo{$comp}{various}{semi_ann_phase} = -(atan2(-$dbSinSemiAnn,$dbCosSemiAnn));
	    if ($modelInfo{$comp}{various}{semi_ann_phase} < 0.) {
	    my ($pi) = atan2(1,1)*4;
	    $modelInfo{$comp}{various}{semi_ann_phase}=$modelInfo{$comp}{various}{semi_ann_phase}+2*$pi;
	}

	    # same for all components.  use later
	    $refX = $dbRefX;
	    $refY = $dbRefY;
	    $refZ = $dbRefZ;

	    $postfitRms{$comp}=$dbPostfitRms;

	    if ($verbose){print STDERR "cc $comp $dbMsStartEpoch $dbMsSlope $dbMsEndEpoch\n"};
	    
	    $modelInfo{$comp}{slopes}{$dbMsStartEpoch} = {
		slope => $dbMsSlope,
		end_epoch => $dbMsEndEpoch,
		slope_sig => $dbMsSlopeSig,
	    };
	    
	  $modelInfo{$comp}{slopeDiffs}{$dbMsdStartEpoch} = {
		diff => $dbMsdDiff,
		diff_sig => $dbMsdDiffSig,
	    };
	    
	  $modelInfo{$comp}{offsets}{$dbMoStartEpoch} = {
		offset => $dbMoOffset,
		offset_sig => $dbMoOffsetSig,
		coseismic => $dbMoCoseismic,
	    };	    
	    	    
	  $modelInfo{$comp}{decays}{$dbMdStartEpoch} = {
		decay => $dbMdDecay,
		decay_sig => $dbMdDecaySig,
		tau => $dbMdTau,
	    };
	    
	    
	    if ($verbose){
		print STDERR "$dbYInt $dbSinAnn $dbCosAnn $dbStartEpoch $dbPostfitRms\n";
		print STDERR "$comp $dbMdStartEpoch $dbMdDecay $dbMdDecaySig $dbMdTau\n";
	    }
	}
	
	my ($localEnd) = (times)[0];
	if ($verbose){printf STDERR "db: %.5f \n",$localEnd-$localStart};
	
	# end component loop
    }
    
    ################################
    # done retrieving model params #
    # calculate modeled coords     #
    ################################

    # TO DO: if variable indicates no slopes retrieved, set coordInfo hash
    # parameter "source" to "mean coordinate" and skip code that attempts
    # to calculate algorithm using slopes, etc.  if slopes were retrieved,
    # set source parameter to "modeled velocity"

    # HERE SET POSTFIT_RMS variables

    for my $comp (@comps) {
	my $href1 = \%{$modelInfo{$comp}{various}};
	my %various = %$href1;

	if ($verbose){print STDERR "various: $siteID  b $various{y_int} $various{sin_ann} $various{cos_ann} $various{sin_semi_ann} $various{cos_semi_ann} $various{start_epoch} $various{end_epoch}\n"};
	
	
	my ($yInt) = $various{y_int};
	my ($yIntSig) = $various{y_int_sig};
	my ($sinAnn) = $various{sin_ann};
	my ($cosAnn) = $various{cos_ann};
	my ($sinSemiAnn) = $various{sin_semi_ann};
	my ($cosSemiAnn) = $various{cos_semi_ann};	
	

	# need to deref hash to get at it
	$href1 = \%{$modelInfo{$comp}{slopes}};
	my %slopes = %$href1;

	my $slope;
	
	for my $startEpoch(sort keys %slopes) {
	    if ($startEpoch) {	    	    
		
		if ($verbose){
		    for my $param (sort keys %{$slopes{$startEpoch}}) {
			print "slopes: $param $startEpoch $slopes{$startEpoch}{$param} ";
		    }
		    print "\n";
		}

		# rosanne's model only requires first slope
		# these are already sorted by date from first to last
		# get first slope and bail
		$slope = $slopes{$startEpoch}{slope};

		last;
	    }
	}
	my ($pi) = atan2(1,1)*4;
	
	###########################################
	# now have parameters needed to calculate #
        # basic model coords at specific date     #
	###########################################

	my ($refCoord);
	
	$refCoord =  
	    $yInt + ($slope * $refEpoch) + 
		($sinAnn * sin($refEpoch * 2 * $pi)) + 
		    ($cosAnn *  cos($refEpoch * 2 * $pi));
	
	$refCoord = 
	    $refCoord + ($sinSemiAnn * sin($refEpoch * 4 * $pi)) + 
		($cosSemiAnn * cos($refEpoch * 4 * $pi));
	
	################################################################
	
	if ($verbose){print "refCoord after slopes $refCoord\n"};

	# complex model parameters:
	# slope diffs (vbreaks)
	my $href2 = \%{$modelInfo{$comp}{slopeDiffs}};
	my %slopeDiffs = %$href2;
	
	for my $startEpoch(sort keys %slopeDiffs) {

	    if ($startEpoch) {	    	    
		my ($dslope) = $slopeDiffs{$startEpoch}{diff};
		my ($year) = substr($startEpoch,0,4);
		my ($doy) = substr($startEpoch,4,3);
		my ($vbreakEpoch) = ConvertDate::ydoy2decyr($year,$doy);
		
		if ($verbose){
		    for my $param (sort keys %{$slopeDiffs{$startEpoch}}) {
			print STDERR "slopeDiffs: $param $startEpoch $slopeDiffs{$startEpoch}{$param} ";
		    }
		    print STDERR "\n";
		}


		# is ref epoch greater than velocity break date?  
		# include following code in calculation of coords
		if ($refEpoch >= $vbreakEpoch) {
		    $refCoord = 
			$refCoord + $dslope * ($refEpoch - $vbreakEpoch);
		}
		
	    }
	}

	if ($verbose){print "refCoord after slopeDiffs: $refCoord\n"};

	# offsets
	my ($href3) = \%{$modelInfo{$comp}{offsets}};
	my %offsets = %$href3;
	for my $startEpoch(sort keys %offsets) {

	    if ($startEpoch) {	    
		my ($offset) = $offsets{$startEpoch}{offset};
		my ($year) = substr($startEpoch,0,4);
		my ($doy) = substr($startEpoch,4,3);
		my ($offsetEpoch) = ConvertDate::ydoy2decyr($year,$doy);
		
		if ($refEpoch >= $offsetEpoch) {
		    $refCoord = 
			$refCoord + $offset;
		
		}
		
		if ($verbose){
		    for my $param (sort keys %{$offsets{$startEpoch}}) {
			print STDERR "offsets: $param $startEpoch $offsets{$startEpoch}{$param} ";
		    }
		    print STDERR "\n";
		}
	    }	
	}
	
	if ($verbose){print "refCoord after offsets: $refCoord\n"};

	# decays
	my ($href4) = \%{$modelInfo{$comp}{decays}};
	my %decays = %$href4;

	for my $startEpoch(sort keys %decays) {
	    
	    if ($startEpoch) {	    
		my ($decay) = $decays{$startEpoch}{decay};
		my ($tau) = $decays{$startEpoch}{tau};
		my ($year) = substr($startEpoch,0,4);
		my ($doy) = substr($startEpoch,4,3);
		my ($tauEpoch) = ConvertDate::ydoy2decyr($year,$doy);
		
		if ($refEpoch >= $tauEpoch) {
		    $refCoord = 
			$refCoord + 
			    ($decay * 
			     exp( -($refEpoch - $tauEpoch) / ($tau / 365))  -
			     $decay);
		}

		if ($verbose){
		    for my $param (sort keys %{$offsets{$startEpoch}}) {
			print STDERR "decays: $param $startEpoch $offsets{$startEpoch}{$param} ";
		    }
		    print STDERR "\n";
		}		

	    }
	}

	if ($verbose){print "refCoord after decays: $refCoord\n"};
	
	$coordInfo{$comp} = $refCoord;       	
	my ($compSigma) = $comp . "_sig";
	$coordInfo{$compSigma} = $various{postfit_rms};

    # END COMPONENT LOOP
    }

    ###########################################   
    # get references to jacobian matrix array # 
    # and jacobian matrix transposed array    #
    ###########################################   

    # refx,y,z, for now, are the same for each component in the db. use in
    # jacobian matrix calculation

    # note: create table in db to hold xyz ref values
    # currently three sets of these values per site (one per neu comp)
    # @jacTr: transposed matrix

    my ($refJac,$refJacTransposed) = &getJacobian($refX,$refY,$refZ);
    
    my (@jac) = @$refJac;
    my (@jacTr)= @$refJacTransposed;

    ###########################
    # calculate reference xyz #
    ###########################

    my ($x,$y,$z);

    $x = ($jacTr[1][1] * $coordInfo{n} + 
	  $jacTr[1][2] * $coordInfo{e} + 
	  $jacTr[1][3] * $coordInfo{u}) / 1000. +
	      $refX;
    
    $y = ($jacTr[2][1] * $coordInfo{n} + 
	  $jacTr[2][2] * $coordInfo{e} + 
	  $jacTr[2][3] * $coordInfo{u}) / 1000. + 
	      $refY;
    
    $z = ($jacTr[3][1] * $coordInfo{n} + 
	  $jacTr[3][2] * $coordInfo{e} + 
	  $jacTr[3][3] * $coordInfo{u}) / 1000. + 
	      $refZ;

    $coordInfo{x} = sprintf ("%13.4f",$x);
    $coordInfo{y} = sprintf ("%13.4f",$y);
    $coordInfo{z} = sprintf ("%13.4f",$z);
    
    ########################
    # calculate xyz sigmas #
    ########################

    my @cov_xyz_epoch;

    if ($postfitRms{n}) {
	$cov_xyz_epoch[1][1] = 
	    $postfitRms{n}**2 * $jacTr[1][1]**2 +  
		$postfitRms{e}**2 * $jacTr[1][2]**2 +
		    $postfitRms{u}**2 * $jacTr[1][3]**2;
	$cov_xyz_epoch[2][2] = 
	    $postfitRms{n}**2 * $jacTr[2][1]**2 +  
		$postfitRms{e}**2 * $jacTr[2][2]**2 +
		    $postfitRms{u}**2 * $jacTr[2][3]**2;
	$cov_xyz_epoch[3][3] = 
	    $postfitRms{n}**2 * $jacTr[3][1]**2 +  
		$postfitRms{e}**2 * $jacTr[3][2]**2 +
		    $postfitRms{u}**2 * $jacTr[3][3]**2;

	my ($xSig,$ySig,$zSig);
	$xSig = sqrt($cov_xyz_epoch[1][1])/1000. ;
	$ySig = sqrt($cov_xyz_epoch[2][2])/1000. ;
	$zSig = sqrt($cov_xyz_epoch[3][3])/1000. ;
	$coordInfo{x_sig} = sprintf("%6.4f",$xSig);
	$coordInfo{y_sig} = sprintf("%6.4f",$ySig);
	$coordInfo{z_sig} = sprintf("%6.4f",$zSig);
    }

    return(\%coordInfo,\%modelInfo);
} 




##############################################################
# GetCoordsFromModelTerms: return xyz, sigmas for epoch      #
# given, using a given hash reference of model terms         #
# provided to this routine
# run model terms through algorithm
#
# arguments: year, day-of-year, hash ref of model terms
##############################################################

sub GetCoordsFromModelTerms {

    use strict;

    my ($year,$doy,$href,$refX,$refY,$refZ,$verbose) = @_;

    # dereference hash ref of model terms
    my (%modelInfo) = %$href;

    # convert year, day to decyr
    #$doy = SOPAC::Utils::formatDay($doy);

    my ($refEpoch) = &ConvertDate::ydoy2decyr($year,$doy);

    ################################
    # connect to db for below code #
    ################################

    ############
    # neu loop #
    ############

    my (%postfitRms,%neuCoordInfo,$xSig,$ySig,$zSig);

    my (@comps) = ("n", "e", "u");
    for my $comp (@comps) {
	my $href1 = \%{$modelInfo{$comp}{various}};
	my %various = %$href1;

	my ($yInt) = $various{y_int};
        if (! defined $yInt) {
            # No motion model - use reference as apriori (short time series)
            return $refX, $refY, $refZ;
        }
	my ($yIntSig) = $various{y_int_sig};
	my ($sinAnn) = $various{sin_ann};
	my ($cosAnn) = $various{cos_ann};
	my ($sinSemiAnn) = $various{sin_semi_ann};
	my ($cosSemiAnn) = $various{cos_semi_ann};	
	$postfitRms{$comp} = $various{postfit_rms};
	
	# need to deref hash to get at it
	$href1 = \%{$modelInfo{$comp}{slopes}};
	my %slopes = %$href1;

	my $slope;
	
	for my $startEpoch(sort keys %slopes) {
	    if ($startEpoch) {	    	    

		if ($verbose){
		    for my $param (sort keys %{$slopes{$startEpoch}}) {
			print "slopes: $param $startEpoch $slopes{$startEpoch}{$param} ";
		    }
		    print "\n";
		}

		# rosanne's model only requires first slope
		# these are already sorted by date from first to last
		# get first slope and bail
		$slope = $slopes{$startEpoch}{slope};


		last;
	    }
	}
	my ($pi) = atan2(1,1)*4;
	
	###########################################
	# now have parameters needed to calculate #
        # basic model coords at specific date     #
	###########################################
	
	my $refCoord = $yInt;

        if (defined $slope) {
            $refCoord += $slope * $refEpoch;
        }
        if (defined $sinAnn) {
            $refCoord += $sinAnn * sin($refEpoch * 2 * $pi);
        }
        if (defined $cosAnn) {
            $refCoord += $cosAnn * cos($refEpoch * 2 * $pi);
        }
	if (defined $sinSemiAnn) {
            $refCoord += $sinSemiAnn * sin($refEpoch * 4 * $pi);
        }
	if (defined $cosSemiAnn) {
            $refCoord += $cosSemiAnn * cos($refEpoch * 4 * $pi);
        }
	
	################################################################
	
	if ($verbose){print "refCoord after slopes: $refCoord\n"};

	# complex model parameters:
	# slope diffs (vbreaks)
	my $href2 = \%{$modelInfo{$comp}{slopeDiffs}};
	my %slopeDiffs = %$href2;
	
	for my $startEpoch(sort keys %slopeDiffs) {

	    if ($startEpoch) {	    	    
		my ($dslope) = $slopeDiffs{$startEpoch}{diff};
		my ($year) = substr($startEpoch,0,4);
		my ($doy) = substr($startEpoch,4,3);
		my ($vbreakEpoch) = ConvertDate::ydoy2decyr($year,$doy);
		
		# is ref epoch greater than velocity break date?  include following
		# code in calculation of coords
		if ($refEpoch >= $vbreakEpoch) {
		    $refCoord = 
			$refCoord + $dslope * ($refEpoch - $vbreakEpoch);
		}
		
		if ($verbose){
		    for my $param (sort keys %{$slopeDiffs{$startEpoch}}) {
			print "decays: $param $startEpoch $slopeDiffs{$startEpoch}{$param} ";
		    }
		    print "\n";
		}		

	    }
	}

	if ($verbose){print "refCoord after slopeDiffs: $refCoord\n"};

	# offsets
	my ($href3) = \%{$modelInfo{$comp}{offsets}};
	my %offsets = %$href3;
	for my $startEpoch(sort keys %offsets) {

	    if ($startEpoch) {	    
		my ($offset) = $offsets{$startEpoch}{offset};
		my ($year) = substr($startEpoch,0,4);
		my ($doy) = substr($startEpoch,4,3);
		my ($offsetEpoch) = ConvertDate::ydoy2decyr($year,$doy);
		
		if ($refEpoch >= $offsetEpoch) {
		    $refCoord = 
			$refCoord + $offset;
		}
		if ($verbose){
		    for my $param (sort keys %{$offsets{$startEpoch}}) {
			print "decays: $param $startEpoch $offsets{$startEpoch}{$param} ";
		    }
		    print "\n";
		}		

	    }	
	}

	if ($verbose){print "refCoord after offsets: $refCoord\n"};
	
	# decays
	my ($href4) = \%{$modelInfo{$comp}{decays}};
	my %decays = %$href4;

	for my $startEpoch(sort keys %decays) {
	    
	    if ($startEpoch) {	    
		my ($decay) = $decays{$startEpoch}{decay};
		my ($tau) = $decays{$startEpoch}{tau};
		my ($year) = substr($startEpoch,0,4);
		my ($doy) = substr($startEpoch,4,3);
		my ($tauEpoch) = ConvertDate::ydoy2decyr($year,$doy);
		
		if ($refEpoch >= $tauEpoch) {
		    $refCoord = 
			$refCoord + 
			    ($decay * 
			     exp( -($refEpoch - $tauEpoch) / ($tau / 365))  -
			     $decay);
		}

		if ($verbose){
		    for my $param (sort keys %{$offsets{$startEpoch}}) {
			print "decays: $param $startEpoch $offsets{$startEpoch}{$param} ";
		    }
		    print "\n";
		}				
	    }
	}
	
	if ($verbose){print "refCoord after decays: $refCoord\n"};
	
	$neuCoordInfo{$comp} = $refCoord;       	
	my ($compSigma) = $comp . "_sig";
	$neuCoordInfo{$compSigma} = $various{postfit_rms};
	
	# END COMPONENT LOOP
    }

    #############################################
    # we now have our neu values for this epoch #
    # convert to xyz 
    #############################################

    ###########################################   
    # get references to jacobian matrix array # 
    # and jacobian matrix transposed array    #
    ###########################################   

    # refx,y,z, for now, are the same for each component in the db. use in
    # jacobian matrix calculation

    # note: create table in db to hold xyz ref values
    # currently three sets of these values per site (one per neu comp)
    # @jacTr: transposed matrix

    my ($refJac,$refJacTransposed) = &getJacobian($refX,$refY,$refZ);
    
    my (@jac) = @$refJac;
    my (@jacTr)= @$refJacTransposed;

    ###########################
    # calculate reference xyz #
    ###########################

    my ($x,$y,$z);

    $x = ($jacTr[1][1] * $neuCoordInfo{n} + 
	  $jacTr[1][2] * $neuCoordInfo{e} + 
	  $jacTr[1][3] * $neuCoordInfo{u}) / 1000. +
	      $refX;
    
    $y = ($jacTr[2][1] * $neuCoordInfo{n} + 
	  $jacTr[2][2] * $neuCoordInfo{e} + 
	  $jacTr[2][3] * $neuCoordInfo{u}) / 1000. + 
	      $refY;
    
    $z = ($jacTr[3][1] * $neuCoordInfo{n} + 
	  $jacTr[3][2] * $neuCoordInfo{e} + 
	  $jacTr[3][3] * $neuCoordInfo{u}) / 1000. + 
	      $refZ;

    ########################
    # calculate xyz sigmas #
    ########################

    my @cov_xyz_epoch;

    if ($postfitRms{n}) {
	$cov_xyz_epoch[1][1] = 
	    $postfitRms{n}**2 * $jacTr[1][1]**2 +  
		$postfitRms{e}**2 * $jacTr[1][2]**2 +
		    $postfitRms{u}**2 * $jacTr[1][3]**2;
	$cov_xyz_epoch[2][2] = 
	    $postfitRms{n}**2 * $jacTr[2][1]**2 +  
		$postfitRms{e}**2 * $jacTr[2][2]**2 +
		    $postfitRms{u}**2 * $jacTr[2][3]**2;
	$cov_xyz_epoch[3][3] = 
	    $postfitRms{n}**2 * $jacTr[3][1]**2 +  
		$postfitRms{e}**2 * $jacTr[3][2]**2 +
		    $postfitRms{u}**2 * $jacTr[3][3]**2;

	$xSig = sqrt($cov_xyz_epoch[1][1])/1000. ;
	$ySig = sqrt($cov_xyz_epoch[2][2])/1000. ;
	$zSig = sqrt($cov_xyz_epoch[3][3])/1000. ;
    }

    return($x,$y,$z,$xSig,$ySig,$zSig);

###############################
# end GetCoordsFromModelTerms
###############################

} 



################################################################
# GetModeledVels: return hash of refined model xyz and wgs/nad #
# velocities for specified epoch                               #
#                                                              #
# arguments: ref to model info, ref epoch, datum (nad/wgs)     #
################################################################

sub GetModeledVels {

    use strict;

    my ($siteID,$href,$refEpoch,$dbh) = @_;
    
    my (%modelInfo) = %$href;
    
    my %slopeInfo;
    for my $comp (sort keys %modelInfo) {
	my $href = \%{$modelInfo{$comp}{slopes}};
	my %slopes = %$href;
	for my $startEpoch(sort keys %slopes) {
	    
	    # we need to assign the first slope in case user wants
	    # slope prior to site coming online
	    $slopeInfo{$comp} = $slopes{$startEpoch}{slope};	
	    my $slopeSig = $comp . "_sig";
	    $slopeInfo{$slopeSig} = $slopes{$startEpoch}{slope_sig};
	    
	    
	    # overwrite velocity so we use last value, unless
	    # start epoch is greater than year/doy provided
	    # to this program
	    my ($year) = substr($startEpoch,0,4);
	    my ($doy) = substr($startEpoch,4,3);
	    
	    my ($decStartEpoch) = ConvertDate::ydoy2decyr($year,$doy);
	    
	    if ($startEpoch && $refEpoch > $decStartEpoch) {	    
		
		$slopeInfo{$comp} = $slopes{$startEpoch}{slope};	
		$slopeInfo{$slopeSig} = $slopes{$startEpoch}{slope_sig};
	    }
	}
    }
    
    # do we have all neu slope values?  if not, skip calc of xyz vels
    my ($xVel,$yVel,$zVel) = 0.0;        
    my ($latVel,$lonVel,$htVel) = 0.0;	
    if ($slopeInfo{n} && $slopeInfo{e} && $slopeInfo{u}) {
	
	# get lat/lon
	# use operational weekly globk as source
	my ($refToGeodArrayRef) = 
	    &SOPAC::SiteCoordinates::Geodetic::get($dbh,
						   {
						       -site_id => $siteID,
						       -precision => "8",
						       -tokens =>
							   ["lat", "lon", "source_id"]
						       }
						   );
	
	if (defined($refToGeodArrayRef)) {
	    
	    # we provided source id, so only get single array returned
	    while (@$refToGeodArrayRef) {
		my ($geodArrayRef) = shift @$refToGeodArrayRef;
		my $lat = $$geodArrayRef[0];
		my $lon = $$geodArrayRef[1];
		
		if ($lat) {	    

		    # vel is same for wgs or nad
		    $latVel = $slopeInfo{n}/1000.;
		    $lonVel = $slopeInfo{e}/1000.;
		    $htVel = $slopeInfo{u}/1000.;		    

		    # get xyz vel
		    ($xVel,$yVel,$zVel) = &PROC::TransformCoords::vneu2vxyz($lat,$lon,$latVel,$lonVel,$htVel);
		    last;
		}
	    }
	}
    }
    return ($xVel,$yVel,$zVel,$latVel,$lonVel,$htVel);
}



sub getJacobian {

    my ($x,$y,$z) = @_;
   
# algorithm from Simon's xyztogeo.c and Rosanne's xyzJacobian.m
# use jac to rotate vectors as
#  
#   n         x             x          n
#   e = jac * y       or    y = jac' * e
#   u         z             z          u
#
#   or 
#
#   neu = xyz * jac'  or   xyz = neu * jac

    my (@jac,@jacTransposed);
    my ($earth_rad) = 6378137.0;
    my ($f) = 1.0 / 298.257222101;
    my ($pi) = atan2(1,1)*4;
    my ($deg2rad) = $pi / 180.0;
    my ($twopi) = $pi * 2.0;
    my ($tolerance) = 0.0001;
    
    my ($eccsq) = 2.0 * $f - $f * $f;
    my ($eq_radius) = sqrt($x*$x+$y*$y);
    my ($lat_p) = atan2($z, $eq_radius);
    my ($lon_i) = atan2($y,$x);
    
    if ($lon_i < 0.0) {
	$lon_i = $lon_i + $twopi;
    }

    my ($h_p) = 0.0;
    my ($niter) = 0;
    my ($converged) = 0;
    
    my ($rad_curve,$rad_lat,$lat_i,$h_i);

    while ($converged == 0) {
	$rad_curve = $earth_rad / sqrt(1.0 - $eccsq * sin($lat_p) * sin($lat_p));
	$rad_lat = $eq_radius * ( 1.0 - $eccsq * $rad_curve / ($rad_curve + $h_p) );
	$lat_i = atan2($z, $rad_lat);
#$h_i;

	if (abs($lat_i) < ($pi / 4.0)) {
	    $h_i = $eq_radius / cos($lat_i) - $rad_curve;
	}
	else {
	    $h_i = $z / sin($lat_i) - (1.0 - $eccsq) * $rad_curve;
	}
    
	if (abs($h_i - $h_p) < $tolerance &&
	    (abs($lat_i - $lat_p) * $rad_curve) < $tolerance) {
	    $converged = 1;
	}
    
	$niter=$niter+1;
	if ($niter > 50) {
	    print STDERR "xyztogeo error : failure to converge";
	    $converged = 1;
	    exit();
	}
	
	$h_p = $h_i;
	$lat_p = $lat_i;
    }

    #jac = [-sin(lat_i)*cos(lon_i)   -sin(lat_i)*sin(lon_i)    cos(lat_i);
    #       -sin(lon_i)               cos(lon_i)               0.0;
    #       cos(lat_i)*cos(lon_i)    cos(lat_i)*sin(lon_i)    sin(lat_i)];

    $jac[1][1] = -sin($lat_i) * cos($lon_i);
    $jac[1][2] = -sin($lat_i) * sin($lon_i);
    $jac[1][3] =  cos($lat_i);
    $jac[2][1] = -sin($lon_i);
    $jac[2][2] =  cos($lon_i);
    $jac[2][3] =  0.0;
    $jac[3][1] =  cos($lat_i) * cos($lon_i);
    $jac[3][2] =  cos($lat_i) * sin($lon_i);
    $jac[3][3] =  sin($lat_i);


    $jacTransposed[1][1] = -sin($lat_i) * cos($lon_i);
    $jacTransposed[1][2] = -sin($lon_i);
    $jacTransposed[1][3] =  cos($lat_i) * cos($lon_i);
    $jacTransposed[2][1] = -sin($lat_i) * sin($lon_i);
    $jacTransposed[2][2] =  cos($lon_i);
    $jacTransposed[2][3] =  cos($lat_i) * sin($lon_i);
    $jacTransposed[3][1] =  cos($lat_i);
    $jacTransposed[3][2] =  0.0;
    $jacTransposed[3][3] =  sin($lat_i);


    return(\@jac,\@jacTransposed);

}


1;
