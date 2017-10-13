#!/usr/bin/perl -w
# code mostly adapted from xml2etc.pl from SIO
# this should determine which sites of a bunch of .trop files are
# within the specified lat-lon box

use strict;


# Run from anywhere
use FindBin;
use lib $FindBin::Bin;

# Perl modules
use Cwd;
use Date::Manip;
use File::Basename;
use File::Path;
use File::Spec;
use Getopt::Long;
use Pod::Usage;

use MetadataFromXML;

# By default the following file will be downloaded and parsed
my $xmlfile="globalProcMetadataInput.xml";
my $URL = "ftp://garner.ucsd.edu/pub/gamit/setup/".$xmlfile;

# File locking constants
use Fcntl qw(:DEFAULT :flock);

# Command line options
my $opt_date1            = undef;
my $opt_date2            = undef;
my $opt_lat1		= undef;
my $opt_lat2		= undef;
my $opt_lon1		= undef;
my $opt_lon2		= undef;
my $opt_force           = 0;
my $opt_help            = undef;
my $opt_input           = $URL;
my $opt_radome          = undef;
my $opt_lookback        = 0;
my $opt_sitestr         = undef;
my $opt_man             = undef;
my $opt_verbose         = undef;
my $opt_dir             = '.';

### Start here
@ARGV > 0 or pod2usage(-verbose => 0);
$| = 1;            # Immediate flush for stdout


### Parse command line options and print usage if requested or error.
GetOptions ('date1=s' => \$opt_date1,
            'lat1=s' => \$opt_lat1,
            'lat2=s' => \$opt_lat2,
            'lon1=s' => \$opt_lon1,
            'lon2=s' => \$opt_lon2,
            'd=s' => \$opt_dir,
            'h'   => \$opt_help,
            'i=s' => \$opt_input,
            'sites=s' => \$opt_sitestr,
            'man' => \$opt_man,
            'v'   => \$opt_verbose,
            ) or pod2usage(-verbose => 0);

### Check options
pod2usage(-verbose => 1) if ($opt_help);
pod2usage(-verbose => 2) if ($opt_man);

if (! defined $opt_date1) {
    pod2usage(-msg => "ERROR: No date1 given. Use the -d1 option.");
    die "No -d1 date1 given";
}
if (! defined $opt_sitestr) {
    pod2usage(-msg => "ERROR: No list of sites given.  Use the -s option.");
    die "No -s sitestr given";
}
if (! defined $opt_input) {
    pod2usage(-msg => "ERROR: No input xml file given. Looking locally.");
    $opt_input="globalProcMetadataInput.xml";
}

my $prog = basename($0, '');

# Lock out additional invocations - see the Camel book chapter 16
#my $lockfile = "/tmp/$prog.lock";
#sysopen(LOCKFH, $lockfile, O_RDONLY | O_CREAT) 
#    or die "Can't open $lockfile: $!";
#flock(LOCKFH, LOCK_EX | LOCK_NB)
#    or die "Can't lock $lockfile: $!";
#if ($opt_verbose) {
#    print "Locked\n";
#}

my $date1 = ParseDate($opt_date1);


my $wd = cwd;
print STDERR "opening metadata object..." ;

my $md = MetadataFromXML->new($opt_input, $opt_verbose);
print STDERR "done\n";

# Construct the directory mapping based on the date range
my %use; my $site4; my %ll;

foreach my $date ($opt_date1) {
    my $pdate = ParseDate($date);
    my ($year, $doy, $month, $mday) = UnixDate($pdate, "%Y", "%j", "%m", "%d");
    my $yydate=substr($date,2,);
    $yydate=~s/-//g;
    
     foreach $site4 (split(' ',$opt_sitestr)) {
            $site4 =~ tr/[A-Z]/[a-z]/;
            my @xyz = $md->get_nominal_xyz($site4, $year, $doy);

            # @sopac maybe SOPAC::SiteCoordinates::Geodetic::get
            my $x=$xyz[0]/1000;
            my $y=$xyz[1]/1000;
            my $z=$xyz[2]/1000;
            my ($lat,$lon,$ht)=xyz2llh($x,$y,$z);
            $ht*=1000; # meters
            $lon+=360;   # for compatibilty with xyz2gd
            if ($lat>$opt_lat1 && $lat <$opt_lat2 && $lon>$opt_lon1+360 && $lon <$opt_lon2+360){ 
              $use{$site4}++ ;
              $ll{$site4}=$lon.' '.$lat.' '.$ht;
            }
#        }       
    }

}
foreach $site4 (sort keys %use) {
  print "$site4 $ll{$site4}\n" if ($use{$site4});
}

sub xyz2llh {                    # taken from Larry Roman's s2cnml
    my ($x, $y, $z)  = @_;       # Input: position  km
                                 # Output: lat lon (deg) ht (km)

    my ($z2, $p2, $p, $r, $mu, $phi, $lat, $lon, $h);
    my $FlatFc =  1.006739514991518;    # IERS2000 standards 1.D0/((1.D0-1.D0/298.25642D0)**2)
    
    my $r2d = 45/atan2(1,1);
    #my $a_e = 6378.1363;               # km IERS Tech Note 13 pg 5
    my $a_e = 6378.1366;               # km IERS2000 standards
    
    #my $f_e = 1/298.257;               # km IERS Tech Note 13 pg 5
    my $f_e =  1/298.25642;             # IERS2000 standards
    
    my $e2 = $f_e *(2 - $f_e);
    
    ($x, $y, $z) = ($x/$a_e, $y/$a_e, $z/$a_e);
    $z2 = $z**2;
    $p2 = $x**2 + $y**2;
    $p = sqrt($p2);
    $r = sqrt($p2 + $z2);
    $mu = atan2($z * (1 - $f_e + $e2 / $r), $p);
    $phi = atan2($z * (1 - $f_e) + $e2 * (sin($mu))**3,
                 (1 - $f_e) * ($p - $e2 * (cos($mu))**3));
    $lat = $phi * $r2d;
    $lon = atan2($y, $x) * $r2d;
    $h = $a_e * ($p * cos($phi) + $z * sin($phi)
                 - sqrt(1 - $e2 * (sin($phi))**2));
    return ($lat, $lon, $h);
}

